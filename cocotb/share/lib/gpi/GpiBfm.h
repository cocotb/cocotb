
#ifndef INCLUDED_GPI_BFM_H
#define INCLUDED_GPI_BFM_H
#include <stdint.h>
#include <string>
#include <vector>
#include "gpi_bfm_api.h"
#include "GpiBfmMsg.h"




class GpiBfm {
public:

	GpiBfm(
			const std::string		&type_name,
			const std::string		&inst_name,
			const std::string		&cls_name,
			cocotb_bfm_notify_f		notify_f,
			void					*notify_data
			);

	virtual ~GpiBfm();

	static int add_bfm(GpiBfm *bfm);

	static const std::vector<GpiBfm *> &get_bfms() { return m_bfm_l; }

	const std::string &get_typename() const { return m_typename; }

	const std::string &get_instname() const { return m_instname; }

	const std::string &get_clsname() const { return m_clsname; }

	int claim_msg();

	GpiBfmMsg *active_msg() const { return m_active_msg; }

	static void set_recv_msg_f(bfm_recv_msg_f *f) { m_recv_msg_f = f; }

protected:

private:
	std::string						m_typename;
	std::string						m_instname;
	std::string						m_clsname;
	cocotb_bfm_notify_f				m_notify_f;
	void							*m_notify_data;
	std::vector<GpiBfmMsg *>		m_msg_queue;
	GpiBfmMsg						*m_active_msg;

	static bfm_recv_msg_f			*m_recv_msg_f;
	static std::vector<GpiBfm *>	m_bfm_l;


};

#endif /* INCLUDED_GPI_BFM_H */
