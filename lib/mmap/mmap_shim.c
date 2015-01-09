//
// In order to trap a call to MMAP we perform the following
// 
// First of all - ptrace the child and detect the call to open()
// 
// If the filename matches a target (e.g. "/dev/mem") we change the argument
// to the system call to /something/else, which allows us to then
// open the same file.
//
// We then trap the call to mmap().  Inspecting the arguments allows us to
// determine the size of the memory region being mapped.  We then update then
// size of our file and mmap it ourselves.
//
// We can then trap all accesses to to the memory region.
//

#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/reg.h>
#include <sys/user.h>
#include <unistd.h>
#include <fcntl.h>
#include <linux/unistd.h>
#include <sys/mman.h>
#include <errno.h>

#include <Python.h>
#include "mmap_shim.h"


#ifdef __x86_64__
// Machine code for:
//  syscall
//  int3            (trap)
#define INJECT_SYSTEM_CALL {0x0f,0x05,0xcc,0}
#define SC_NUMBER  (8 * ORIG_RAX)
#define SC_RETCODE (8 * RAX)
#define INSTRUCTION_POINTER(regs) regs.rip
#define XAX_REGISTER(regs) regs.rax
#define XBX_REGISTER(regs) regs.rbx
#define XCX_REGISTER(regs) regs.rcx
#define XDX_REGISTER(regs) regs.rdx
#define XDI_REGISTER(regs) regs.rdi
#define XBP_REGISTER(regs) regs.rbp
#define XSI_REGISTER(regs) regs.rsi
#define XR8_REGISTER(regs) regs.r8
#define XR9_REGISTER(regs) regs.r9
#define XR10_REGISTER(regs) regs.r10

// FIXME
#define MMAP_SYSCALL 9
#define OPEN_SYSCALL 2
#define MPROTECT_SYSCALL 10

#define OPEN_ARG_FILENAME XDI_REGISTER
#define OPEN_ARG_FLAGS XSI_REGISTER
#define OPEN_ARG_MODE XDX_REGISTER

#define MMAP_ARG_LENGTH XSI_REGISTER
#define MMAP_ARG_FD XR8_REGISTER
#define MMAP_ARG_OFFSET XR9_REGISTER

#define MPROTECT_ARG_START XDI_REGISTER
#define MPROTECT_ARG_LEN XSI_REGISTER
#define MPROTECT_ARG_PROT XDX_REGISTER


#else   // 32-bit system
// Machine code for:
//  int $0x80       (system call)
//  int3            (trap)
#define INJECT_SYSTEM_CALL {0xcd,0x80,0xcc,0}
#define SC_NUMBER  (4 * ORIG_EAX)
#define SC_RETCODE (4 * EAX)
#define INSTRUCTION_POINTER(regs) regs.eip
#define XAX_REGISTER(regs) regs.eax
#define XBX_REGISTER(regs) regs.ebx
#define XCX_REGISTER(regs) regs.ecx
#define XDX_REGISTER(regs) regs.edx
#define XDI_REGISTER(regs) regs.edi
#define XBP_REGISTER(regs) regs.ebp
#define MMAP_SYSCALL __NR_mmap2
#define OPEN_SYSCALL __NR_open
#define MPROTECT_SYSCALL __NR_mprotect

// System call tables are different?!
#define OPEN_ARG_FILENAME XBX_REGISTER
#define OPEN_ARG_FLAGS XCX_REGISTER
#define OPEN_ARG_MODE XDX_REGISTER

#define MMAP_ARG_LENGTH XCX_REGISTER
#define MMAP_ARG_FD XDI_REGISTER
#define MMAP_ARG_OFFSET XBP_REGISTER

#define MPROTECT_ARG_START XBX_REGISTER
#define MPROTECT_ARG_LEN XCX_REGISTER
#define MPROTECT_ARG_PROT XDX_REGISTER

#endif

// Python read function just takes an offset in bytes and a buffer
static PyObject *pWrFunction;

// Python read function just takes an offset in bytes and returns a value
static PyObject *pRdFunction;

// The filename we catch an open call to
static char *fname;

// The filename we use as a replacement
static char *replacement_fname;


// Functions called by Python
static PyObject *set_write_function(PyObject *self, PyObject *args) {

    pWrFunction = PyTuple_GetItem(args, 0);
    Py_INCREF(pWrFunction);

    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}

static PyObject *set_read_function(PyObject *self, PyObject *args) {

    pRdFunction = PyTuple_GetItem(args, 0);
    Py_INCREF(pRdFunction);

    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}


// Set the fname
static PyObject *set_mmap_fname(PyObject *self, PyObject *args) {
    PyObject *pFnameStr= PyTuple_GetItem(args, 0);
    const char *py_str = PyString_AsString(pFnameStr);

    int len = strnlen(py_str, 1024);

    fname = (char*)malloc((len+1)*sizeof(char));
    replacement_fname = (char*)malloc((len+1)*sizeof(char));

    fname = strncpy(fname, py_str, strnlen(py_str, 1024) + 1);

    // New filename length must be less than or equal to length original
    if (len<6) {
        printf("Unable to generate replacement fname?!\n");
        *replacement_fname = "/_f";
    } else {
        replacement_fname = strncpy(replacement_fname, "/tmp/_", 6);
    }
    printf("Set fname to %s\n", fname);
    printf("Set new fname to %s\n", replacement_fname);
    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}


// Functions called by C (exported in a shared library)
uint32_t sim_read32(uint32_t address, uint32_t *buffer) {

    if (!PyCallable_Check(pRdFunction)) {
        printf("Read function not callable...\n");
        return 0;
    }

    PyObject *call_args = PyTuple_New(1);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(address));

    rv = PyObject_CallObject(pRdFunction, call_args);
    *buffer = PyInt_AsLong(rv);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return 1;
}

uint32_t sim_write32(uint32_t address, uint32_t value) {

    if (!PyCallable_Check(pWrFunction)) {
        printf("Write function isn't callable...\n");
        return 0;
    }

    PyObject *call_args = PyTuple_New(2);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(address));
    PyTuple_SetItem(call_args, 1, PyInt_FromLong(value));

    rv = PyObject_CallObject(pWrFunction, call_args);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return 1;
}




static const char * request_to_string(int request)
{
    switch (request) {
    case PTRACE_SYSCALL:
        return "PTRACE_SYSCALL";
    case PTRACE_SETOPTIONS:
        return "PTRACE_SETOPTIONS";
    case PTRACE_PEEKUSER:
        return "PTRACE_PEEKUSER";
    case PTRACE_GETREGS:
        return "PTRACE_GETREGS";
    case PTRACE_SETREGS:
        return "PTRACE_SETREGS";
    case PTRACE_SINGLESTEP:
        return "PTRACE_SINGLESTEP";
    case PTRACE_PEEKDATA:
        return "PTRACE_PEEKDATA";
    case PTRACE_POKEDATA:
        return "PTRACE_POKEDATA";
    case PTRACE_CONT:
        return "PTRACE_CONT";
    default:
        return "unknown";
    }
}


static inline long __check_ptrace(enum __ptrace_request request, pid_t pid,
                                                        void *addr, void *data)
{
    long rc = ptrace(request, pid, addr, data);
#ifndef TRACE_PTRACE
    if (rc < 0 && (request != PTRACE_PEEKDATA && request != PTRACE_PEEKUSER)) {
#endif
        int errsv = errno;
        printf("%s:%d in %s:\t", __FILE__, __LINE__, __func__);
        printf("ptrace(request=%d (%s), pid=%d, addr=%p, data=%p) returned %ld (errno: %d %s)\n",
                request, request_to_string(request), pid, addr, data, rc, errsv, strerror(errsv));
#ifndef TRACE_PTRACE
    }
#endif
    return rc;
}

const int long_size = sizeof(long);

static void getdata(pid_t child, long addr, char *str, int len)
{   char *laddr;
    int i, j;
    union u {
            long val;
            char chars[long_size];
    }data;
    i = 0;
    j = len / long_size;
    laddr = str;
    while(i < j) {
        data.val = ptrace(PTRACE_PEEKDATA,
                          child, addr + i * long_size,
                          NULL);
        memcpy(laddr, data.chars, long_size);
        ++i;
        laddr += long_size;
    }
    j = len % long_size;
    if(j != 0) {
        data.val = ptrace(PTRACE_PEEKDATA,
                          child, addr + i * long_size,
                          NULL);
        memcpy(laddr, data.chars, j);
    }
    str[len] = '\0';
}


static void putdata(pid_t child, long addr, char *str, int len)
{   char *laddr;
    int i, j;
    union u {
            long val;
            char chars[long_size];
    }data;
    i = 0;
    j = len / long_size;
    laddr = str;
    while(i < j) {
        memcpy(data.chars, laddr, long_size);
        ptrace(PTRACE_POKEDATA, child,
               addr + i * long_size, data.val);
        ++i;
        laddr += long_size;
    }
    j = len % long_size;
    if(j != 0) {
        data.val = ptrace(PTRACE_PEEKDATA, child, addr + i * long_size, NULL);
        memcpy(data.chars, laddr, j);
        ptrace(PTRACE_POKEDATA, child, addr + i * long_size, data.val);
    }
}

// This function calls mprotect with PROT flags for a process that's
// been stopped by a signal
static int inject_mprotect_from_sig(pid_t child, void *addr, size_t len, int prot)
{
    char code[] = INJECT_SYSTEM_CALL;
    char orig[7];
    int status;
    int rc = -1;
    struct user_regs_struct regs;
    struct user_regs_struct orig_regs;

    __check_ptrace(PTRACE_GETREGS, child, NULL, &regs);
    __check_ptrace(PTRACE_GETREGS, child, NULL, &orig_regs);
    getdata(child, INSTRUCTION_POINTER(regs), orig, 7);
    XAX_REGISTER(regs) = MPROTECT_SYSCALL;
    MPROTECT_ARG_START(regs) = (unsigned long)addr;
    MPROTECT_ARG_LEN(regs) = len;
    MPROTECT_ARG_PROT(regs) = prot;
    putdata(child, INSTRUCTION_POINTER(regs), code, 3);
    __check_ptrace(PTRACE_SETREGS, child, NULL, &regs);

    // System call entry
    __check_ptrace(PTRACE_SYSCALL, child, NULL, NULL);
    wait(&status);
    __check_ptrace(PTRACE_GETREGS, child, NULL, &regs);
    if (WSTOPSIG(status) != SIGTRAP) {
        fprintf(stderr, "Got status=%d at eip: %llx but was expecting sigtrap\n",
                                            status, INSTRUCTION_POINTER(regs));
        goto done;
    }

    // System call exit
    __check_ptrace(PTRACE_SYSCALL, child, NULL, NULL);
    wait(&status);
    __check_ptrace(PTRACE_GETREGS, child, NULL, &regs);
    if (WSTOPSIG(status) != SIGTRAP) {
        fprintf(stderr, "Got status=%d at eip: %llx but was expecting sigtrap\n",
                                            status, INSTRUCTION_POINTER(regs));
        goto done;
    }

    rc = __check_ptrace(PTRACE_PEEKUSER, child, (void *)SC_RETCODE, NULL);

    if (rc) {
        fprintf(stderr, "Injected call to mprotect failed with %d\n", rc);
        goto done;
    }

    __check_ptrace(PTRACE_CONT, child, NULL, NULL);
    wait(&status);
    __check_ptrace(PTRACE_GETREGS, child, NULL, &regs);
    if (WSTOPSIG(status) != SIGTRAP) {
        fprintf(stderr, "Got status=%d at eip: %llx but was expecting sigtrap\n",
                                            status, INSTRUCTION_POINTER(regs));
        rc = -1;
    }

done:
    putdata(child, INSTRUCTION_POINTER(orig_regs), orig, 3);
    __check_ptrace(PTRACE_SETREGS, child, NULL, &orig_regs);
    return rc;
}



typedef enum {
        DETECT_OPEN_ENTRY,
        MODIFY_OPEN_EXIT,
        DETECT_MMAP_ENTRY,
        DETECT_MMAP_EXIT,
        MPROTECT_MEMORY_REGION,
        TRAP_ACCESS,
        CHECK_WRITE_ACCESS,
        UPDATE_WRITE_VALUE,
        READ_CYCLE,
        POST_READ_CLEANUP
} state_e;




static PyObject *execute(PyObject *self, PyObject *args) {

    const char *prog;
    void *ptr = NULL;
    pid_t child;
    int status;
    int p_reason;
    long sc_number;
    char *str;
    struct user_regs_struct regs;
    struct user_regs_struct saved_regs;
    size_t           length  = 0;
    siginfo_t        siginfo;
    void *           base    = NULL;
    uint32_t         access  = 0;
    uint32_t         read_value;
    int              child_fd = -1;

    if (!PyArg_ParseTuple(args, "s", &prog)) {
        PyErr_SetString(PyExc_ValueError, "Unable to parse program agrument");
        return NULL;
    }

    if (fname == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "No call to set_mmap_fname has been made");
        return NULL;
    }

    // Create our shared memory region
    int fd = open(replacement_fname, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
    if (fd < 0)
        return NULL;

    state_e state;

    state = DETECT_OPEN_ENTRY;



    child = fork();

    if(child == 0) {
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        /* Stop before doing anything, giving parent a chance to catch the exec: */
        kill(getpid(), SIGSTOP);
        execl(prog, "", NULL);
    } else {

        // PTRACE_O_EXITKILL only in new linux >= 3.8
#if defined ( PTRACE_O_EXITKILL )
        ptrace(PTRACE_SETOPTIONS, child, NULL, PTRACE_O_EXITKILL);
#else
        ptrace(PTRACE_SETOPTIONS, child, NULL, PTRACE_O_TRACEEXIT);
#endif


        while(1) {
            wait(&status);
            p_reason = PTRACE_SYSCALL;

            if (WIFEXITED(status)) {
                printf("Child exit with status %d\n", WEXITSTATUS(status));
                break;
            }
            if (WIFSIGNALED(status)) {
                printf("Child exit due to signal %d\n", WTERMSIG(status));
                break;
            }
            if (!WIFSTOPPED(status)) {
                printf("wait() returned unhandled status 0x%x\n", status);
                break;
            }
            if (WSTOPSIG(status) == SIGBUS) {
                fprintf(stderr, "Child got SIGBUS, something is very wrong!\n");
                return NULL;
            }

            ptrace(PTRACE_GETREGS, child, NULL, &regs);

            sc_number = -1;
            if (WSTOPSIG(status) == SIGTRAP) {
                sc_number = ptrace(PTRACE_PEEKUSER, child, SC_NUMBER, NULL);
            }

            switch (state) {

                case DETECT_OPEN_ENTRY:
                    if (OPEN_SYSCALL == sc_number) {
                        ptrace(PTRACE_GETREGS, child, NULL, &regs);
                        fflush(stdout);
                        str = (char *)calloc(9, sizeof(char));
                        getdata(child, OPEN_ARG_FILENAME(regs), str, 9);
                        if (!strncmp(fname, str, strlen(fname))) {
                            OPEN_ARG_FLAGS(regs) |= O_CREAT | O_APPEND | O_RDWR;
                            OPEN_ARG_MODE(regs) |= S_IRUSR | S_IWUSR;
                            putdata(child, OPEN_ARG_FILENAME(regs), replacement_fname, strlen(replacement_fname)+1);
                            ptrace(PTRACE_SETREGS, child, NULL, &regs);
                            getdata(child, OPEN_ARG_FILENAME(regs), str, 9);
                            state = MODIFY_OPEN_EXIT;
                        }
                    }
                    break;

                case MODIFY_OPEN_EXIT:
                    ptrace(PTRACE_GETREGS, child, NULL, &regs);
                    child_fd = XAX_REGISTER(regs);
                    state = DETECT_MMAP_ENTRY;
                    break;

                case DETECT_MMAP_ENTRY:

                    if (MMAP_SYSCALL == sc_number) {

                        ptrace(PTRACE_GETREGS, child, NULL, &regs);
                        length = MMAP_ARG_LENGTH(regs);

                        // Mapping our file
                        if (child_fd == MMAP_ARG_FD(regs)) {
                            base = (void *)MMAP_ARG_OFFSET(regs);
                            if (ftruncate(fd, length)) {
                                fprintf(stderr, "ftruncate failed\n");
                                return NULL;
                            }
                            ptr = mmap(NULL, PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
                            if (MAP_FAILED == ptr) {
                                fprintf(stderr, "Unable to mmap the file in our local process\n");
                                return NULL;
                            }

                            // Update pgoff so it works on a file
                            MMAP_ARG_OFFSET(regs) = 0;

                            ptrace(PTRACE_SETREGS, child, NULL, &regs);
                            state = DETECT_MMAP_EXIT;
                        }
                    }
                    break;

                case DETECT_MMAP_EXIT:
                    if (MMAP_SYSCALL == sc_number) {
                        ptrace(PTRACE_GETREGS, child, NULL, &regs);
                        base = (void *)XAX_REGISTER(regs);
                        state = MPROTECT_MEMORY_REGION;
                        p_reason = PTRACE_SINGLESTEP;
                    }
                    break;

                case MPROTECT_MEMORY_REGION:
                    if (WSTOPSIG(status) == SIGTRAP) {
                        if (inject_mprotect_from_sig(child, base, length, PROT_NONE))
                            return NULL;
                        state = TRAP_ACCESS;
                        p_reason = PTRACE_CONT;
                    } else {
                        fprintf(stderr, "Was expecting a SIGTRAP after a PTRACE_SINGLESTEP?!\n");
                        return NULL;
                    }
                    break;

                // To reach here, the child has mapped the memory region, we've
                // sneakily called mprotect from the child process so that any
                // access to the region will cause a SIGSEGV which we trap
                case TRAP_ACCESS:
                    if (WSTOPSIG(status) != SIGSEGV) {
                        p_reason = PTRACE_CONT;
                        break;
                    }

                    ptrace(PTRACE_GETREGS, child, NULL, &saved_regs);
                    ptrace(PTRACE_GETSIGINFO, child, NULL, &siginfo);

                    access = siginfo.si_addr - base;

                    // Allow read access and let the child try again
                    if (inject_mprotect_from_sig(child, base, length, PROT_READ))
                        return NULL;

                    state = CHECK_WRITE_ACCESS;
                    p_reason = PTRACE_SINGLESTEP;
                    break;

                case CHECK_WRITE_ACCESS:

                    // Still a segfault - must be a write
                    if (WSTOPSIG(status) == SIGSEGV) {
                        if (inject_mprotect_from_sig(child, base, length, PROT_WRITE))
                            return NULL;

                        state = UPDATE_WRITE_VALUE;
                        p_reason = PTRACE_SINGLESTEP;

                    // Otherwise it's a read
                    } else if (WSTOPSIG(status) == SIGTRAP) {
                        sim_read32(access, &read_value);
                        *(uint32_t *)(ptr + access) = read_value;

                        // Set the instruction pointer back to the read instruction and repeat the read
                        ptrace(PTRACE_SETREGS, child, NULL, &saved_regs);
                        state = READ_CYCLE;
                        p_reason = PTRACE_SINGLESTEP;
                    } else {
                        fprintf(stderr, "Some kind of error occurred!\n");
                        return NULL;
                    }
                    break;

                case UPDATE_WRITE_VALUE:
                    if (WSTOPSIG(status) != SIGTRAP) {
                        fprintf(stderr, "Some kind of error occured, was expecting a single step\n");
                        return NULL;
                    }

                    read_value = *(uint32_t *)(ptr + access);
                    sim_write32(access, read_value);

                    if (inject_mprotect_from_sig(child, base, length, PROT_NONE))
                        return NULL;
                    state = TRAP_ACCESS;
                    p_reason = PTRACE_CONT;
                    break;

                // Step through the read
                case READ_CYCLE:
                    if (WSTOPSIG(status) != SIGTRAP) {
                        fprintf(stderr, "Some kind of error occured, was expecting a single step\n");
                        return NULL;
                    }

                    state = POST_READ_CLEANUP;
                    p_reason = PTRACE_SINGLESTEP;
                    break;

                case POST_READ_CLEANUP:
                    if (inject_mprotect_from_sig(child, base, length, PROT_NONE))
                        return NULL;
                    state = TRAP_ACCESS;
                    p_reason = PTRACE_CONT;
                    break;
            }

            ptrace(p_reason, child, NULL, NULL);
        }
    }

    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}


static const char * state_to_string(state_e state)
{
    switch (state) {
    case DETECT_OPEN_ENTRY:
        return "DETECT_OPEN_ENTRY";
    case MODIFY_OPEN_EXIT:
        return "MODIFY_OPEN_EXIT";
    case DETECT_MMAP_ENTRY:
        return "DETECT_MMAP_ENTRY";
    case DETECT_MMAP_EXIT:
        return "DETECT_MMAP_EXIT";
    case MPROTECT_MEMORY_REGION:
        return "MPROTECT_MEMORY_REGION";
    case TRAP_ACCESS:
        return "TRAP_ACCESS";
    case CHECK_WRITE_ACCESS:
        return "CHECK_WRITE_ACCESS";
    case UPDATE_WRITE_VALUE:
        return "UPDATE_WRITE_VALUE";
    case READ_CYCLE:
        return "READ_CYCLE";
    case POST_READ_CLEANUP:
        return "POST_READ_CLEANUP";
    default:
        return "unknown";
    }
}


PyMODINIT_FUNC
initmmap_shim(void)
{
    PyObject* mmap_shim;
    mmap_shim = Py_InitModule("mmap_shim", MMAPShimMethods);
}


