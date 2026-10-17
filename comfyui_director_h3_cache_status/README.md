# Director Studio · H3 Server Status API + Windows Tray

This is a read-only ComfyUI companion for the server meter shown immediately to
the right of `ESTIMATE` in MiniMax H3 Director Cut Studio. The installer also
adds a hidden Windows Tray monitor with login auto-start.

Right-click the Tray icon and choose `Settings...` to configure the refresh
interval (2-300 seconds), monitored ComfyUI URL/IP and monitored H3 Relay cache
folder. Saving applies the new interval and endpoint immediately. The cache
path is persisted to this custom node's `status-settings.json`, so Studio and
Tray report the same folder without restarting ComfyUI.

Install this complete folder on the ComfyUI server as:

```text
ComfyUI/custom_nodes/comfyui_director_h3_cache_status/
```

Restart ComfyUI. The companion exposes only:

```text
GET /director_studio/h3-relay-cache-status
```

The response contains Cache total bytes, file count, scan-error count, aggregate
direct-child sizes, CPU, DRAM, GPU and VRAM percentages. It does not return
process lists, filenames, download files, delete cache data or follow symbolic
links. Resource samples refresh per request while the recursive Cache scan is
reused for 30 seconds.

If the companion is absent or the server cannot be reached, Studio deliberately
shows N/A for every unavailable value instead of incorrectly reporting zero.

Recommended installation from the Studio folder:

```bat
install_h3_cache_status_server.bat "D:\ComfyUI" "http://192.168.0.185:8189"
```

