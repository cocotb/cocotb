// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_UTILS_H_
#define COCOTB_UTILS_H_

#define xstr(a) str(a)
#define str(a) #a

template <typename F>
class Deferable {
  public:
    constexpr Deferable(F f) : f_(f) {};
    ~Deferable() { f_(); }

  private:
    F f_;
};

template <typename F>
constexpr Deferable<F> make_deferable(F f) {
    return Deferable<F>(f);
}

#define DEFER1(a, b) a##b
#define DEFER0(a, b) DEFER1(a, b)
#define DEFER(statement) \
    auto DEFER0(_defer, __COUNTER__) = make_deferable([&]() { statement; });

#endif /* COCOTB_UTILS_H_ */
