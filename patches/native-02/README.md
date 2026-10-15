# GFG Native FG — Patch 02 (Steam Deck Vulkan present flags)

For installed `v2.1.2-native.1` or the previous sRGB Patch 01.
**Not a GitHub Release and not a full program install.**

### Cause confirmed from Deck log
`flags=0xc0` means `VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR` (0x40)
and `VK_SWAPCHAIN_CREATE_PRESENT_WAIT_2_BIT_KHR` (0x80).
`format=44` is BGRA8_UNORM (not sRGB), `imageUsage=0x1b` includes
both transfer-source and transfer-destination usages.

### Fix
- Permit only the 0x40 and 0x80 presentation-protocol flags.
- Keep protected, mutable-format, unknown or other unverified flags rejected.
- When the app already requests both copy usages, preserve its original
  VkSwapchainCreateInfoKHR including flags and pNext; do not require a separate
  surface-capability query or modify creation.
- Continue real-frame fallback on other unsupported WSI configurations.
- CI directly tests the observed 0xc0/format=44/0x1b policy.

### Install
Close the game and extract this patch; in Konsole from its folder:

```bash
bash apply.sh
```

Your existing `~/.local/bin/gfg-native %command%` launch option stays the same.
The old .so is saved beside the installed one as `*.before-patch-02`.
No elevated privileges are needed. This does not replace existing GFG Extreme
or install MAKO or Lossless.dll.

### Rollback
```bash
bash rollback.sh
```

### Diagnostic
`GFG_NATIVE_TRACE=1 ~/.local/bin/gfg-native %command% > "$HOME/gfg-native-test.log" 2>&1`

Expected for the observed Deck request:
`swapchain 1280x800 candidate=1 ... reason=existing-usage-ready ... flags=0xc0 ...`.
This only confirms eligibility. The next distinct stage is
`OWN TE8 CPU bridge active`; actual synthetic WSI submission is
`generated=...`. Real display delivery and performance remain unverified.

The patch contains only a replacement Vulkan shared library and
install/rollback/checksum documents; it is not a new release.
