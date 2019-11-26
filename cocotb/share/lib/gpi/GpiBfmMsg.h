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
#ifndef INCLUDED_GPI_BFM_MSG_H
#define INCLUDED_GPI_BFM_MSG_H
#include <vector>
#include <string>
#include <utility>
#include <stdint.h>
#include "cocotb_bfm_api.h"

struct GpiBfmMsg {
public:
	struct MsgParam {
		std::string			str;
		union {
			uint64_t			ui64;
			int64_t				i64;
		} int_v;
	};

	enum MsgParamType {
		ParamType_Str,
		ParamType_Si,
		ParamType_Ui
	};

	GpiBfmMsg(
			uint32_t 				id,
			int32_t					paramc=-1,
			cocotb_bfm_msg_param_t	*paramv=0);

	virtual ~GpiBfmMsg();

	uint32_t id() const { return m_id; }

	void add_param_ui(uint64_t p);

	void add_param_si(int64_t p);

	void add_param_s(const char *p);

	void add_param(const cocotb_bfm_msg_param_t *p);

	uint32_t num_params() const { return m_param_l_idx; }

	const cocotb_bfm_msg_param_t *get_param();

	cocotb_bfm_msg_param_t *get_param_l() const { return m_param_l; }

	const cocotb_bfm_msg_param_t *get_param(uint32_t idx) const;

	uint64_t get_param_ui();

	int64_t get_param_si();

	const char *get_param_str();

protected:

private:
	uint32_t								m_id;
	cocotb_bfm_msg_param_t					*m_param_l;
	uint32_t								m_param_l_idx;
	uint32_t								m_param_l_max;

	std::vector<std::string>				m_str_l;
	uint32_t								m_idx;

};

#endif /* INCLUDED_GPI_BFM_MSG_H */

