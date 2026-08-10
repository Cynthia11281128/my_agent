# VPN Route Split for SSH

## Settings / Inputs

This workflow configures Windows routing so a specific SSH server bypasses a full-tunnel VPN while other traffic can continue to use the VPN.

- VPN client: `<vpn-client>`
- SSH alias: `<server-alias>`
- SSH host: `<server-host>`
- SSH port: `<ssh-port>`
- SSH user: `<ssh-user>`
- Local non-VPN gateway: `<local-gateway>`
- Local non-VPN interface: `<local-interface>`
- Current resolved server IP: `<server-ip>`

Run PowerShell as Administrator for route changes.

## Task Description

Keep the VPN connected for tools that require it, while routing SSH traffic to a remote server through the local network interface to improve VS Code Remote SSH, terminal, and remote file or image browsing performance.

## Workflow Summary

1. Inspect the SSH configuration to identify the effective host and port:

   ```bash
   ssh -G <server-alias> | rg "^(hostname|user|port|identityfile) "
   ```

2. Resolve the SSH host to its current IPv4 address in Administrator PowerShell:

   ```powershell
   $hostName = "<server-host>"
   $ip = (Resolve-DnsName $hostName -Type A | Where-Object { $_.IPAddress } | Select-Object -First 1 -ExpandProperty IPAddress)
   $ip
   ```

3. Select the active local network interface that is not the VPN adapter:

   ```powershell
   $gw = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" -and $_.InterfaceAlias -notmatch "Cisco|AnyConnect|VPN" } | Select-Object -First 1
   $gw.InterfaceAlias
   $gw.IPv4DefaultGateway.NextHop
   ```

4. Add a host route for the resolved server IP through the local gateway:

   ```powershell
   New-NetRoute -DestinationPrefix "$ip/32" -InterfaceIndex $gw.InterfaceIndex -NextHop $gw.IPv4DefaultGateway.NextHop -RouteMetric 1
   ```

5. Verify TCP connectivity and selected route:

   ```powershell
   Test-NetConnection $ip -Port <ssh-port> -InformationLevel Detailed
   ```

6. Connect through SSH or VS Code Remote SSH using either the host name or the fixed IP:

   ```powershell
   ssh -p <ssh-port> <ssh-user>@<server-ip>
   ```

7. If stable VS Code behavior is preferred, pin the SSH config to the resolved IP:

   ```sshconfig
   Host <server-alias>
     HostName <server-ip>
     User <ssh-user>
     Port <ssh-port>
     IdentityFile <identity-file>
   ```

8. To revert and let the server use the default route again, remove the static host route:

   ```powershell
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -Confirm:$false
   ```

   If needed, remove both route stores explicitly:

   ```powershell
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -PolicyStore ActiveStore -Confirm:$false
   Remove-NetRoute -DestinationPrefix "<server-ip>/32" -PolicyStore PersistentStore -Confirm:$false
   ```

## Verification

- `Test-NetConnection` succeeded for the SSH IP and port.
- The selected interface was the local Ethernet interface.
- The selected next hop was the local gateway.
- The result confirmed the SSH route was using the non-VPN path.
- `tracert` was not used as the final proof because ICMP timeouts can occur even when TCP connectivity works.

## Final State

- A static host route exists for `<server-ip>/32` through `<local-gateway>`.
- SSH and VS Code Remote SSH traffic to `<server-ip>:<ssh-port>` should use the local network interface.
- VPN-dependent tools can continue to use the VPN for other destinations.

## Failed Attempts / Notes

- Long copied PowerShell commands can break if line wrapping splits command names or parameters. Running the commands one line at a time avoids parser errors.
- `Resolve-DnsName` can return records without an `IPAddress` property first, so filter with `Where-Object { $_.IPAddress }`.
- If the SSH host later resolves to a different IP, add a new route for the new IP or update the pinned SSH config.
- If the VPN client enforces strict full-tunnel policy, local split routing may be blocked by VPN policy.

## Placeholder Values

- `<vpn-client>`: Cisco AnyConnect
- `<server-alias>`: seeta
- `<server-host>`: connect.bjb2.seetacloud.com
- `<ssh-port>`: 52496
- `<ssh-user>`: root
- `<local-gateway>`: 10.10.64.1
- `<local-interface>`: Ethernet interface displayed as `以太网`
- `<server-ip>`: 106.38.204.136
- `<identity-file>`: the SSH identity file configured for the server alias
