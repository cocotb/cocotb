package cocotb_array_pkg;

    typedef logic               [2:0] test_array_entry_t;
    typedef test_array_entry_t  [2:0] test_2d_array_t;
    typedef test_2d_array_t     [2:0] test_3d_array_t;

    typedef struct packed {
        logic [2:0]                 vect_packed;
        logic [2:0][2:0]            vect_packed_packed;
        test_array_entry_t          array_packed;
        test_array_entry_t [2:0]    array_packed_packed;
    } struct_packed_t;

endpackage
