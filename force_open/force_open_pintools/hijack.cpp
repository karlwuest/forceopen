#include <iostream>
#include <fstream>
#include <map>
#include "pin.H"

ifstream BranchFile;
map<string, map<long long, long long> > branches;


KNOB<string> KnobBranchFile(KNOB_MODE_WRITEONCE, "pintool",
    "b", "branches", "specify branch file name");

VOID ImageLoad(IMG img, VOID *v)
 {
    if (branches.find(IMG_Name(img)) == branches.end()) {
        /* don't output information about this module */
        return;
    }
    map<long long, long long> &img_branches = branches[IMG_Name(img)];
    /* loop through all instructions */
    for (SEC sec = IMG_SecHead(img); SEC_Valid(sec); sec = SEC_Next(sec)) {
        for (RTN rtn = SEC_RtnHead(sec); RTN_Valid(rtn); rtn = RTN_Next(rtn)) {
            RTN_Open(rtn);
            for (INS ins = RTN_InsHead(rtn); INS_Valid(ins); ins = INS_Next(ins)) {
                long long ins_addr = INS_Address(ins);
                long long base_addr = IMG_LowAddress(img);
                if (INS_IsDirectBranch(ins) && img_branches.find(ins_addr - base_addr) != img_branches.end()) {
                    /* insert jump */
                    ADDRINT target_addr = (ADDRINT) (base_addr + img_branches[ins_addr - base_addr]);
                    INS_InsertDirectJump(ins, IPOINT_BEFORE, target_addr);
                }
            }
            RTN_Close(rtn);
        }
    }
 }


/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    cerr << "This tool hijacks the execution of a program" << endl;
    cerr << endl << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */
/*   argc, argv are the entire command line: pin -t <toolname> -- ...    */
/* ===================================================================== */

int main(int argc, char * argv[])
{
    // Initialize pin
    if (PIN_Init(argc, argv)) return Usage();

    BranchFile.open(KnobBranchFile.Value().c_str());
    string mod;
    long long from, to;
    while (BranchFile >> mod >> from >> to) {
        branches[mod][from] = to;
    }
    BranchFile.close();

    // Register Instruction to be called to instrument instructions
    //INS_AddInstrumentFunction(Instruction, 0);

    // Register ImageLoad to be called at every module load
    IMG_AddInstrumentFunction(ImageLoad, 0);


    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}

