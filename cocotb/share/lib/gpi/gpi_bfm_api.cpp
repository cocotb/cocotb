/****************************************************************************
 * gpi_bfm_api.cpp
 ****************************************************************************/
#include "gpi_bfm_api.h"
#include "GpiBfm.h"

int cocotb_bfm_register(
		const char				*type_name,
		const char				*inst_name,
		const char				*cls_name,
		cocotb_bfm_notify_f		notify_f,
		void					*notify_data) {

	return GpiBfm::add_bfm(new GpiBfm(
			type_name,
			inst_name,
			cls_name,
			notify_f,
			notify_data
			));
}

// Returns the number of registered BFMs
int cocotb_bfm_num_registered(void) {
	return GpiBfm::get_bfms().size();
}

// Returns the type name of the specified BFM
const char *cocotb_bfm_typename(int id) {
	return GpiBfm::get_bfms().at(id)->get_typename().c_str();
}

// Returns the instance name of the specified BFM
const char *cocotb_bfm_instname(int id) {
	return GpiBfm::get_bfms().at(id)->get_instname().c_str();
}

// Returns the class name of the specified BFM
const char *cocotb_bfm_clsname(int id) {
	return GpiBfm::get_bfms().at(id)->get_clsname().c_str();
}

//
int cocotb_bfm_claim_msg(int id) {
	return GpiBfm::get_bfms().at(id)->claim_msg();
}

uint64_t cocotb_bfm_get_ui_param(int id) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(id);
	GpiBfmMsg *msg = bfm->active_msg();

	if (msg) {
		return msg->get_param_ui();
	} else {
		return 0;
	}
}

int64_t cocotb_bfm_get_si_param(int id) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(id);
	GpiBfmMsg *msg = bfm->active_msg();

	if (msg) {
		return msg->get_param_si();
	} else {
		return 0;
	}
}

const char *cocotb_bfm_get_str_param(int id) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(id);
	GpiBfmMsg *msg = bfm->active_msg();

	if (msg) {
		return msg->get_param_str();
	} else {
		return 0;
	}
}
