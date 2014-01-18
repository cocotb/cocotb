#define _GNU_SOURCE

#include <sys/mman.h>
#include <dlfcn.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <stdint.h>
#include <string.h>

#define X86_EFLAGS_TF   0x00000100

typedef struct {
    int                 mapped_fd;
    int                 write;
    void                *address;
    size_t              length;
    off_t               offset;
    void                *buffer;
} trap_info_t;

static trap_info_t      trap;

static void hdl_sigsegv(int sig, siginfo_t *siginfo, void *context) {

    ucontext_t *c = context;

//     printf("Trapped access to address 0x%lx (offset 0x%x) IP=%x ERR: %x\n", siginfo->si_addr, siginfo->si_addr-trap.buffer, c->uc_mcontext.gregs[REG_RIP], c->uc_mcontext.gregs[REG_ERR]);

    // Check access is actually into our memory region
    // (don't want to mask genuine segfaults)
    if ((void *) siginfo->si_addr < trap.buffer || 
            (void *) siginfo->si_addr >= trap.buffer + trap.length) {

        printf("It was a genuine segfault?!");
        abort ();
    }

    if (mprotect((void *)trap.buffer, trap.length, PROT_READ|PROT_WRITE)==-1) {
        perror("mprotect");
    }

    trap.address = siginfo->si_addr;
    trap.write = (c->uc_mcontext.gregs[REG_ERR] & 0x02)>>1;

    if (trap.write) {
        printf("Trapped write access to 0x%08x (offset 0x%04x)\n", trap.address, siginfo->si_addr-trap.buffer);
    } else {
        printf("Trapped read access to 0x%08x (offset 0x%04x)\n", trap.address, siginfo->si_addr-trap.buffer);
        if (!sim_read32((uint32_t)(siginfo->si_addr-trap.buffer), (uint32_t *)siginfo->si_addr))
            printf("Read from offset 0x08%x failed\n", siginfo->si_addr-trap.buffer);
    }
//     switch (trap.phase) {
// 
//         case TRAP_ALL:
//             printf("In trap all, calling mprotect to allow writes\n");
// 
//             if (mprotect((void *)trap.buffer, trap.length, PROT_NONE)==-1) {
//                 perror("mprotect");
//             }
// 
//             trap.phase = TRAP_READ;
//             break;
// 
//         case TRAP_READ:
//             printf("Trapped read access to offset 0x%x -> setting to 0xFFFFFFFF!\n", siginfo->si_addr-trap.buffer);
// 
//             if (mprotect((void *)trap.buffer, trap.length, PROT_WRITE)==-1) {
//                 perror("mprotect");
//             }
// 
//             *(uint32_t *)siginfo->si_addr ^= 0xFFFFFFFF;
// 
//             // Permit access
//             if (mprotect((void *)trap.buffer, trap.length, PROT_READ)==-1) {
//                 perror("mprotect");
//             }
// 
//             trap.phase = TRAP_ALL;
//             break;
//     }

    // Set trap flag in the user context
    c->uc_mcontext.gregs[REG_EFL] |= X86_EFLAGS_TF;
}

static void hdl_sigtrap(int sig, siginfo_t *siginfo, void *context) {

    // Unset the trap flag!
    ucontext_t *c = context;
    c->uc_mcontext.gregs[REG_EFL] ^= X86_EFLAGS_TF;

    if (trap.write) {
        if (!sim_write32((uint32_t)(siginfo->si_addr-trap.buffer), *(uint32_t *)trap.address))
            printf("Write 0x%08x to offset 0x08%x failed\n", *(uint32_t *)trap.address, trap.address-trap.buffer);
    }

    trap.write = 0;
    // Set up memory protection so that we can trap accesses
    if (mprotect((void *)trap.buffer, trap.length, PROT_NONE)==-1) {
        perror("mprotect");
    }
    
//     printf("Trapped SIGTRAP IP=%x\n", c->uc_mcontext.gregs[REG_RIP]);


//     if (mprotect((void *)trap.buffer, trap.length, PROT_READ)==-1) {
//         perror("mprotect");
//     }
// 
//     if (trap.phase == TRAP_READ) {
//         printf("Trapped write access to %lu (value %d)\n", trap.address, *(uint32_t *)trap.address);
//         trap.phase = TRAP_ALL;
//     }


}

// static void *buffer;
// static size_t size;

int open(const char *pathname, int flags) {

    if (!strncmp(pathname, "/dev/mem", 8)) {
        printf("Intercepted open on /dev/mem, returning 49845\n");
        trap.mapped_fd = 49845;
        return 49845;
    }

    void *(*original_open)(const char *pathname, int flags);

    original_open = dlsym(RTLD_NEXT, "open");

    return original_open(pathname, flags);
}


void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset) {

    printf("Intercepted mmap call for %lu (fd=%d)\n", offset, fd);

    void *(*original_mmap)(void *addr, size_t length, int prot, int flags,
                                                        int fd, off_t offset);
    original_mmap = dlsym(RTLD_NEXT, "mmap");
    if (fd != trap.mapped_fd) {
        original_mmap(addr, length, prot, flags, fd, offset);
        return;
    }

    trap.write  = 0;
    trap.length = length;
    trap.offset = offset;

    // Allocate the memory aligned to the page size
    int pagesize = sysconf(_SC_PAGE_SIZE);
    trap.buffer = memalign(pagesize, length);

    if (!trap.buffer) {
        perror("memalign");
        return (void *) -1;
    }
    memset(trap.buffer, 0, length);

    // Set up memory protection so that we can trap accesses
    if (mprotect((void *)trap.buffer, length, PROT_NONE)==-1) {
        perror("mprotect");
        return (void *) -1;
    }

    // Set up SEGFAULT handler
    struct sigaction act;
    act.sa_sigaction = &hdl_sigsegv;
    act.sa_flags = SA_SIGINFO;

    if (sigaction(SIGSEGV, &act, NULL) < 0) {
        perror ("sigaction");
        return (void *) -1;
    }

    // Set up SEGFAULT handler
    struct sigaction trap_act;
    trap_act.sa_sigaction = &hdl_sigtrap;
    trap_act.sa_flags = SA_SIGINFO;

    if (sigaction(SIGTRAP, &trap_act, NULL) < 0) {
        perror ("sigaction");
        return (void *) -1;
    }


    return trap.buffer;
}

