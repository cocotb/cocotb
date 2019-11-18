
import argparse
import importlib
import cocotb
from cocotb.bfms import BfmMgr
from string import Template

def bfm_load_modules(module_l): 
    for m in module_l:
        try:
            importlib.import_module(m)
        except Exception as e:
            print("Error: failed to load module \"" + str(m) + "\": " + str(e))
            raise e

def process_template_vl(template, info):
    t = Template(template)
    
    bfm_import_calls = ""
    for i in range(len(info.import_info)):
        imp = info.import_info[i]
        bfm_import_calls += "              " + str(i) + ": begin\n"
        bfm_import_calls += "                  " + imp.T.__name__  + "\n"
        bfm_import_calls += "              end\n"
        
    bfm_export_tasks = ""
    for i in range(len(info.export_info)):
        exp = info.export_info[i]
        bfm_export_tasks += "    task " + exp.T.__name__ + "("
        bfm_export_tasks += ");\n"
        bfm_export_tasks += "    begin\n"
        bfm_export_tasks += "        $cocotb_bfm_begin_msg(bfm_id, " + str(i) + ");\n"
        bfm_export_tasks += "        $cocotb_bfm_end_msg(bfm_id);\n"
        bfm_export_tasks += "    end\n"
        bfm_export_tasks += "    endtask\n"
        
    
    impl_param_m = {
        "bfm_classname" : info.T.__module__ + "." + info.T.__qualname__,
        "bfm_import_calls" : bfm_import_calls,
        "bfm_export_tasks" : bfm_export_tasks
        }
    
    cocotb_bfm_api_impl = '''
    reg signed[31:0]      bfm_id;
    event                 bfm_ev;
    reg signed[31:0]      bfm_msg_id;
    
${bfm_export_tasks}
    
    initial begin
      bfm_id = $cocotb_bfm_register("${bfm_classname}", bfm_ev);
      
      while (1) begin
          bfm_msg_id = $cocotb_bfm_claim_msg(bfm_id);
          
          case (bfm_id)
${bfm_import_calls}
              -1: begin
                  @(bfm_ev);
              end
          endcase
          
      end
    end
    '''
   
    param_m = {
        "cocotb_bfm_api_impl" : Template(cocotb_bfm_api_impl).safe_substitute(impl_param_m)
        }
    
    
    return t.safe_substitute(param_m)

def bfm_generate_vl(args):
    inst = BfmMgr.inst()
    
    out = open(args.o, "w")
    out.write("//***************************************************************************\n")
    out.write("//* BFMs file for CocoTB. \n")
    out.write("//* Note: This file is generated. Do Not Edit\n")
    out.write("//***************************************************************************\n")

    for t in inst.bfm_type_info_m.keys():
        info = inst.bfm_type_info_m[t]
        
        if cocotb.bfm_vlog not in info.hdl.keys():
            raise Exception("BFM \"" + t.__name__ + "\" does not support Verilog")
        
        template_f = open(info.hdl[cocotb.bfm_vlog], "r")
        template = template_f.read()
        template_f.close()
        
        out.write(process_template_vl(template, info))
        
    out.close()
        
def bfm_generate(args):
    '''
    Generates BFM files required for simulation
    '''
    print("bfm_generate")
    
    if args.o is None:
        if args.language == "vlog":
            args.o = "cocotb_bfms.v"
        elif args.language == "sv":
            args.o = "cocotb_bfms.sv"
        elif args.language == "vhdl":
            args.o = "cocotb_bfms.vhdl"
            
    if args.language == "vlog":
        bfm_generate_vl(args)
    elif args.language == "sv":
        args.o = "cocotb_bfms.sv"
    elif args.language == "vhdl":
        args.o = "cocotb_bfms.vhdl"
            
    
def bfm_list(args):
    print("bfm_list")
    inst = BfmMgr.inst()
    
    print("inst=" + str(inst))

    print("Number of keys: " + str(len(inst.bfm_type_info_m.keys())))
    for t in inst.bfm_type_info_m.keys():
        print("BFM: \"" + str(t) + "\"")

def main():
    parser = argparse.ArgumentParser(prog="cocotb-bfms")
    
    subparser = parser.add_subparsers()
    generate_cmd = subparser.add_parser("generate")
    generate_cmd.set_defaults(func=bfm_generate)
    generate_cmd.add_argument("-m", action='append')
    generate_cmd.add_argument("-language", default="vlog")
    generate_cmd.add_argument("-o", default=None)
    
    list_cmd = subparser.add_parser("list")
    list_cmd.set_defaults(func=bfm_list)
    list_cmd.add_argument("-m", action='append')
    
    args = parser.parse_args()
 
    # Ensure the BfmMgr is created
    BfmMgr.inst()
    
    if hasattr(args, 'm'):
        bfm_load_modules(args.m)
        
    args.func(args)
    
    
if __name__ == "__main__":
    main()