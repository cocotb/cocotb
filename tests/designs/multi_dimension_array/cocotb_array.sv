import cocotb_array_pkg::*;

module cocotb_array (

  //INPUTS
  
  //Single dimensions
  input     logic               [2:0]               in_vect_packed                                      ,
  input     logic                                   in_vect_unpacked[2:0]                               ,
  input     test_array_entry_t                      in_arr                                              ,
        
  //2 dimensions        
  input     logic               [2:0][2:0]          in_2d_vect_packed_packed                            ,
  input     logic               [2:0]               in_2d_vect_packed_unpacked[2:0]                     ,
  input     logic                                   in_2d_vect_unpacked_unpacked[2:0][2:0]              ,
        
  input     test_array_entry_t  [2:0]               in_arr_packed                                       ,
  input     test_array_entry_t                      in_arr_unpacked[2:0]                                ,
  input     test_2d_array_t                         in_2d_arr                                           ,
  
  //3 dimensions
  input     logic               [2:0][2:0][2:0]     in_vect_packed_packed_packed                        ,
  input     logic               [2:0][2:0]          in_vect_packed_packed_unpacked[2:0]                 ,
  input     logic               [2:0]               in_vect_packed_unpacked_unpacked[2:0][2:0]          ,
  input     logic                                   in_vect_unpacked_unpacked_unpacked[2:0][2:0][2:0]   ,

  input     test_array_entry_t  [2:0][2:0]          in_arr_packed_packed                                ,
  input     test_array_entry_t  [2:0]               in_arr_packed_unpacked[2:0]                         ,
  input     test_array_entry_t                      in_arr_unpacked_unpacked[2:0][2:0]                  ,

  input     test_2d_array_t     [2:0]               in_2d_arr_packed                                    ,
  input     test_2d_array_t                         in_2d_arr_unpacked[2:0]                             ,
  
  input     test_3d_array_t                         in_3d_arr                                           ,
  
  
  //OUTPUTS
  //Single dimensions
  output    logic               [2:0]               out_vect_packed                                     ,
  output    logic                                   out_vect_unpacked[2:0]                              ,
  output    test_array_entry_t                      out_arr                                             ,
        
  //2 dimensions        
  output    logic               [2:0][2:0]          out_2d_vect_packed_packed                           ,
  output    logic               [2:0]               out_2d_vect_packed_unpacked[2:0]                    ,
  output    logic                                   out_2d_vect_unpacked_unpacked[2:0][2:0]             ,
        
  output    test_array_entry_t  [2:0]               out_arr_packed                                      ,
  output    test_array_entry_t                      out_arr_unpacked[2:0]                               ,
  output    test_2d_array_t                         out_2d_arr                                          ,
  
  //3 dimensions
  output    logic               [2:0][2:0][2:0]     out_vect_packed_packed_packed                       ,
  output    logic               [2:0][2:0]          out_vect_packed_packed_unpacked[2:0]                ,
  output    logic               [2:0]               out_vect_packed_unpacked_unpacked[2:0][2:0]         ,
  output    logic                                   out_vect_unpacked_unpacked_unpacked[2:0][2:0][2:0]  ,

  output    test_array_entry_t  [2:0][2:0]          out_arr_packed_packed                               ,
  output    test_array_entry_t  [2:0]               out_arr_packed_unpacked[2:0]                        ,
  output    test_array_entry_t                      out_arr_unpacked_unpacked[2:0][2:0]                 ,

  output    test_2d_array_t     [2:0]               out_2d_arr_packed                                   ,
  output    test_2d_array_t                         out_2d_arr_unpacked[2:0]                            ,
  
  output    test_3d_array_t                         out_3d_arr                                          

);

//Fairly simple passthrough of all the values...

assign out_vect_packed                                      = in_vect_packed                                      ;
assign out_vect_unpacked                                    = in_vect_unpacked                                    ;
assign out_arr                                              = in_arr                                              ;
                                                            
                                                            
assign out_2d_vect_packed_packed                            = in_2d_vect_packed_packed                            ;
assign out_2d_vect_packed_unpacked                          = in_2d_vect_packed_unpacked                          ;
assign out_2d_vect_unpacked_unpacked                        = in_2d_vect_unpacked_unpacked                        ;
                                                            
assign out_arr_packed                                       = in_arr_packed                                       ;
assign out_arr_unpacked                                     = in_arr_unpacked                                     ;
assign out_2d_arr                                           = in_2d_arr                                           ;
                                                            
                                                            
assign out_vect_packed_packed_packed                        = in_vect_packed_packed_packed                        ;
assign out_vect_packed_packed_unpacked                      = in_vect_packed_packed_unpacked                      ;
assign out_vect_packed_unpacked_unpacked                    = in_vect_packed_unpacked_unpacked                    ;
assign out_vect_unpacked_unpacked_unpacked                  = in_vect_unpacked_unpacked_unpacked                  ;
                                                            
assign out_arr_packed_packed                                = in_arr_packed_packed                                ;
assign out_arr_packed_unpacked                              = in_arr_packed_unpacked                              ;
assign out_arr_unpacked_unpacked                            = in_arr_unpacked_unpacked                            ;
                                                            
assign out_2d_arr_packed                                    = in_2d_arr_packed                                    ;
assign out_2d_arr_unpacked                                  = in_2d_arr_unpacked                                  ;
                                                            
assign out_3d_arr                                           = in_3d_arr                                           ;



endmodule;
