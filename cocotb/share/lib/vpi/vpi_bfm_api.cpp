#include "vpi_bfm_api.h"
#include "vpi_user.h"
#include "gpi_bfm_api.h"

static void cocotb_bfm_notify(void *notify_ev) {

}

static int cocotb_bfm_register_tf(char *user_data) {
	// Obtain arguments
	// - type_name -- passed in
	// - inst_name -- callsite?
	// - cls_name  -- passed in
	const char *type_name = 0;
	const char *inst_name = 0;
	const char *cls_name = 0;
	vpiHandle notify_ev = 0;
	int id;

	(void)id;

	id = cocotb_bfm_register(
			type_name,
			inst_name,
			cls_name,
			&cocotb_bfm_notify,
			notify_ev
			);

	// TODO: set return value



	return 0;
}

void register_bfm_tf(void) {
	s_vpi_systf_data tf_data;

	// cocotb_bfm_register
	// cocotb_bfm_next_message
	// cocotb_bfm_get_param_i32
	// cocotb_bfm_get_param_ui32
	// cocotb_bfm_get_param_i64
	// cocotb_bfm_get_param_ui64

	tf_data.type = vpiSysFunc;
	tf_data.tfname = "$cocotb_bfm_register";
	tf_data.calltf = &cocotb_bfm_register_tf;
	tf_data.compiletf = 0;
	tf_data.sizetf = 0;
	tf_data.user_data = 0;
	vpi_register_systf(&tf_data);

}
