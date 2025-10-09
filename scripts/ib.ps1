param([Parameter(ValueFromRemainingArguments=$true)] $Args)
$env:PYTHONPATH = "src"
& .\.venv\Scripts\python.exe -m hybrid_ai_trading.utils @Args
