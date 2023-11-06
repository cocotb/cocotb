// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_EXPORTS_H_
#define COCOTB_EXPORTS_H_

// Make cocotb work correctly when the default visibility is changed to hidden
// Changing the default visibility to hidden has the advantage of significantly
// reducing the code size and load times, as well as letting the optimizer
// produce better code.
#if _WIN32
#define COCOTB_EXPORT __declspec(dllexport)
#define COCOTB_IMPORT __declspec(dllimport)
#else
#define COCOTB_EXPORT __attribute__((visibility("default")))
#define COCOTB_IMPORT
#endif

#endif
