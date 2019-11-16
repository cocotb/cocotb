
#include "GpiBfmMsg.h"

GpiBfmMsg::GpiBfmMsg(
		uint32_t 				id,
		int32_t					paramc,
		gpi_bfm_msg_param_t		*paramv) {
	m_id = id;
	m_idx = 0;
}

GpiBfmMsg::~GpiBfmMsg() {

}

void GpiBfmMsg::add_param_ui(uint64_t p) {
	gpi_bfm_msg_param_t param;
	param.ptype = GpiBfmParamType_Ui;
	param.pval.ui64 = p;
	m_param_l.push_back(param);
}

void GpiBfmMsg::add_param_i(int64_t p) {
	gpi_bfm_msg_param_t param;
	param.ptype = GpiBfmParamType_Si;
	param.pval.i64 = p;
	m_param_l.push_back(param);
}

void GpiBfmMsg::add_param_s(const char *p) {
	gpi_bfm_msg_param_t param;
	param.ptype = GpiBfmParamType_Si;
	m_str_l.push_back(p);
	param.pval.str = m_str_l.at(m_str_l.size()-1).c_str();
	m_param_l.push_back(param);
}

const gpi_bfm_msg_param_t *GpiBfmMsg::get_param() {
	gpi_bfm_msg_param_t *ret = 0;
	if (m_idx < m_param_l.size()) {
		ret = &m_param_l.at(m_idx);
		m_idx++;
	}
	return ret;
}

const gpi_bfm_msg_param_t *GpiBfmMsg::get_param(uint32_t idx) const {
	const gpi_bfm_msg_param_t *ret = 0;
	if (idx < m_param_l.size()) {
		ret = &m_param_l.at(idx);
	}
	return ret;
}

uint64_t GpiBfmMsg::get_param_ui() {
	uint64_t ret = 0;
	if (m_idx < m_param_l.size()) {
		ret = m_param_l.at(m_idx).pval.ui64;
		m_idx++;
	}
	return ret;
}

int64_t GpiBfmMsg::get_param_si() {
	int64_t ret = 0;
	if (m_idx < m_param_l.size()) {
		ret = m_param_l.at(m_idx).pval.i64;
		m_idx++;
	}
	return ret;
}

const char *GpiBfmMsg::get_param_str() {
	const char *ret = "";
	if (m_idx < m_param_l.size()) {
		ret = m_param_l.at(m_idx).pval.str;
		m_idx++;
	}
	return ret;
}

