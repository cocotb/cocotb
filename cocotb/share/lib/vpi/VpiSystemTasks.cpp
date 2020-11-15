#include "vpi_user.h"
#include "gpi.h"
#include "../gpi/gpi_priv.h"


namespace {

struct end_test_info {
    gpi_event_t level;
    char const * msg;
};

int end_test_calltf(char * userdata)
{
    end_test_info info = *((end_test_info *)userdata);
    gpi_embed_event(info.level, info.msg);
    return 0;
}

end_test_info test_pass = {SIM_TEST_PASS, "Simulator requesting passing test end"};
end_test_info test_fail = {SIM_TEST_FAIL, "Simulator requesting failing test end"};

}

void register_system_functions()
{
    s_vpi_systf_data tfData;
    tfData.type         = vpiSysTask;
    tfData.sysfunctype  = vpiSysTask;
    tfData.calltf       = end_test_calltf;
    tfData.compiletf    = NULL;
    tfData.sizetf       = NULL;

    tfData.user_data    = (char *)&test_pass;
    tfData.tfname       = "$cocotb_pass_test";
    vpi_register_systf( &tfData );

    tfData.user_data    = (char *)&test_fail;
    tfData.tfname       = "$cocotb_fail_test";
    vpi_register_systf( &tfData );

}
