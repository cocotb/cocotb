$j = Start-Job -ScriptBlock { SxsTrace Trace -logfile:SxsTrace.etl }
Start-Sleep -s 5
python -c "import cocotb.simulator"
Start-Sleep -s 5
$j | Stop-Job
SxsTrace Stoptrace
SxsTrace Parse -logfile:SxsTrace.etl -outfile:SxsTrace.txt
Get-Content SxsTrace.txt
