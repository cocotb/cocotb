#include "GpiBfm.h"
#include <stdio.h>

GpiBfm::GpiBfm(
		const std::string		&type_name,
		const std::string		&inst_name,
		const std::string		&cls_name,
		cocotb_bfm_notify_f		notify_f,
		void					*notify_data) :
		m_typename(type_name),
		m_instname(inst_name),
		m_clsname(cls_name),
		m_notify_f(notify_f),
		m_notify_data(notify_data) {
	m_active_msg = 0;
}

GpiBfm::~GpiBfm() {
	if (m_active_msg) {
		delete m_active_msg;
		m_active_msg = 0;
	}

}

int GpiBfm::add_bfm(GpiBfm *bfm) {
	int ret = m_bfm_l.size();

	m_bfm_l.push_back(bfm);

	return ret;
}

void GpiBfm::send_msg(GpiBfmMsg *msg) {
	m_msg_queue.push_back(msg);
	fprintf(stdout, "GpiBfm::send_msg notify_f=%p\n", m_notify_f);
	if (m_notify_f) {
		m_notify_f(m_notify_data);
	}
}

int GpiBfm::claim_msg() {
	if (m_active_msg) {
		delete m_active_msg;
		m_active_msg = 0;
	}
	if (m_msg_queue.size() > 0) {
		m_active_msg = m_msg_queue.at(0);
		m_msg_queue.erase(m_msg_queue.begin());
		return m_active_msg->id();
	} else {
		return -1;
	}
}

std::vector<GpiBfm *> GpiBfm::m_bfm_l;
bfm_recv_msg_f GpiBfm::m_recv_msg_f = 0;

