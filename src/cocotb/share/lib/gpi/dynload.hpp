// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_DYNLOAD_HPP_
#define COCOTB_DYNLOAD_HPP_

void *utils_dyn_open(const char *lib_name);
void *utils_dyn_sym(void *handle, const char *sym_name);

#endif /* COCOTB_DYNLOAD_HPP_ */
