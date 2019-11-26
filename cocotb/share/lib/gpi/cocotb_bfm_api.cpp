/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* Copyright (c) 2013 SolarFlare Communications Inc
* Copyright (c) 2019 Matthew Ballance
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd,
*       SolarFlare Communications Inc nor the
*      names of its contributors may be used to endorse or promote products
*      derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/
#include <stdio.h>
#include "cocotb_bfm_api.h"
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

void cocotb_bfm_begin_msg(uint32_t bfm_id, uint32_t msg_id) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);

	bfm->begin_inbound_msg(msg_id);
}

void cocotb_bfm_add_si_param(uint32_t bfm_id, int64_t pval) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
	GpiBfmMsg *msg = bfm->active_inbound_msg();

	if (msg) {
		msg->add_param_si(pval);
	} else {
		fprintf(stdout, "Error: attempting to add an signed parameter to a NULL message\n");
	}
}

void cocotb_bfm_add_ui_param(uint32_t bfm_id, uint64_t pval) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
	GpiBfmMsg *msg = bfm->active_inbound_msg();

	if (msg) {
		msg->add_param_ui(pval);
	} else {
		fprintf(stdout, "Error: attempting to add an unsigned parameter to a NULL message\n");
	}
}

void cocotb_bfm_end_msg(uint32_t bfm_id) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);

	bfm->send_inbound_msg();
}

void cocotb_bfm_send_msg(
		uint32_t				bfm_id,
		uint32_t				msg_id,
		uint32_t				paramc,
		cocotb_bfm_msg_param_t	*paramv) {
	GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
	GpiBfmMsg *msg = new GpiBfmMsg(msg_id, paramc, paramv);
	bfm->send_msg(msg);
}

void cocotb_bfm_set_recv_msg_f(bfm_recv_msg_f recv_msg_f) {
	GpiBfm::set_recv_msg_f(recv_msg_f);
}
