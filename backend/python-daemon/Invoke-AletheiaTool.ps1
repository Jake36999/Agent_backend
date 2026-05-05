function Invoke-AletheiaTool {
  param(
    [Parameter(Mandatory=$true)][string]$ToolName,
    [Parameter(Mandatory=$true)][hashtable]$Args,
    [int]$Id = 1,
    [int]$TimeoutMs = 240000
  )

  $client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 8765)
  $stream = $client.GetStream()
  $stream.ReadTimeout = $TimeoutMs
  $stream.WriteTimeout = $TimeoutMs

  $writer = [System.IO.StreamWriter]::new($stream)
  $reader = [System.IO.StreamReader]::new($stream)
  $writer.NewLine = "`n"
  $writer.AutoFlush = $true

  try {
    $req = @{
      jsonrpc = "2.0"
      id = $Id
      method = "tools.call"
      params = @{
        toolName = $ToolName
        args = $Args
      }
    } | ConvertTo-Json -Depth 20 -Compress

    $writer.WriteLine($req)
    $line = $reader.ReadLine()
    return ($line | ConvertFrom-Json)
  }
  finally {
    $client.Close()
  }
}
