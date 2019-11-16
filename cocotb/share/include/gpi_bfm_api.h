
#ifndef INCLUDED_GPI_BFM_API_H
#define INCLUDED_GPI_BFM_API_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Callback function type used to notify
// implementation when a message is available
typedef void (*cocotb_bfm_notify_f)(void *);

int cocotb_bfm_register(
		const char				*type_name,
		const char				*inst_name,
		const char				*cls_name,
		cocotb_bfm_notify_f		notify_f,
		void					*notify_data);

// Returns the number of registered BFMs
int cocotb_bfm_num_registered(void);

// Returns the type name of the specified BFM
const char *cocotb_bfm_typename(int id);

// Returns the instance name of the specified BFM
const char *cocotb_bfm_instname(int id);

// Returns the class name of the specified BFM
const char *cocotb_bfm_clsname(int id);

// Claims the next message in the queue.
// If none is available, returns -1
int cocotb_bfm_claim_msg(int id);

// Get an unsigned-integer parameter from the active message
uint64_t cocotb_bfm_get_ui_param(int id);

// Get an signed-integer parameter from the active message
int64_t cocotb_bfm_get_si_param(int id);

// Get a string parameter from the active message
const char *cocotb_bfm_get_str_param(int id);


// Init call to register Python module
void cocotb_bfm_api_init(void);

typedef enum {
	GpiBfmParamType_Ui,
	GpiBfmParamType_Si,
	GpiBfmParamType_Str
} gpi_bfm_param_type_e;

typedef struct gpi_bfm_msg_param_s {
	gpi_bfm_param_type_e	ptype;
	union {
		const char			*str;
		uint64_t			ui64;
		int64_t				i64;
	} pval;
} gpi_bfm_msg_param_t;

/**
 * Send a message to a specific BFM
 */
void gpi_bfm_send_msg(
		uint32_t			bfm_id,
		uint32_t			msg_id,
		uint32_t			paramc,
		gpi_bfm_msg_param_t	*paramv);

/**
 * Callback function type to receive
 * messages from BFMs
 */
typedef void (*bfm_recv_msg_f)(
		uint32_t 			bfm_id,
		uint32_t 			msg_id,
		uint32_t			paramc,
		gpi_bfm_msg_param_t	*paramv);

void gpi_bfm_set_recv_msg_f(
		bfm_recv_msg_f		recv_msg_f);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_GPI_BFM_API_H */
