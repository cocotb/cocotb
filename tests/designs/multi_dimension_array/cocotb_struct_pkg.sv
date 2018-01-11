package cocotb_struct_pkg;

    typedef logic               [2:0] test_array_entry_t;
    typedef test_array_entry_t  [2:0] test_2d_array_t;
    typedef test_2d_array_t     [2:0] test_3d_array_t;

    typedef struct packed {
        logic [2:0]                 vect_packed;
        logic [2:0][2:0]            vect_packed_packed;
        test_array_entry_t          array_packed;
        test_array_entry_t [2:0]    array_packed_packed;
    } struct_packed_t;

    typedef struct_packed_t [2:0]       struct_packed_arr_packed_t;
    typedef struct_packed_t             struct_packed_arr_unpacked_t [2:0];

    typedef struct_packed_t [2:0][2:0]  struct_packed_arr_packed_packed_t;
    typedef struct_packed_t [2:0]       struct_packed_arr_packed_unpacked_t [2:0];
    typedef struct_packed_t             struct_packed_arr_unpacked_unpacked_t [2:0][2:0];
    
    typedef struct unpacked {
        logic [2:0]                 vect_packed;
        logic                       vect_unpacked[2:0];
        
        logic [2:0]                 vect_packed_unpacked[2:0];
        logic                       vect_unpacked_unpacked[2:0];

        test_array_entry_t          array_packed;
        test_array_entry_t [2:0]    array_packed_packed;
        test_array_entry_t          array_packed_unpacked[2:0];
        
        test_array_entry_t [2:0]    array_packed_packed_unpacked[2:0];
    } struct_unpacked_t;

endpackage
