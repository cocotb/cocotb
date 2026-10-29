# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Run this script with:
# powershell -executionpolicy bypass -File tests\sxs.ps1

$j = Start-Job -ScriptBlock { SxsTrace Trace -logfile:SxsTrace.etl }
Start-Sleep -s 5
python -c "import cocotb.simulator"
Start-Sleep -s 5
$j | Stop-Job
SxsTrace Stoptrace
SxsTrace Parse -logfile:SxsTrace.etl -outfile:SxsTrace.txt
Get-Content SxsTrace.txt
