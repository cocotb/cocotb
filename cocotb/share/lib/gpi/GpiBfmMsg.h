
#ifndef INCLUDED_GPI_BFM_MSG_H
#define INCLUDED_GPI_BFM_MSG_H
#include <vector>
#include <string>
#include <utility>
#include <stdint.h>
#include "gpi_bfm_api.h"

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

