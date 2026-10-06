# GFG Governor v0.0.1 Beta.2 test report

- Python unit/regression/service tests: 97/97 PASS
- Python compileall: PASS
- Decky compiled frontend `node --check`: PASS
- Frontend/backend RPC parity: 37 RPCs, 0 missing backend methods
- UI architecture assertions: PASS
  - Governor-first home exists
  - Frame Generation is a dedicated screen
  - Scaling is a dedicated screen
  - Advanced hub is task-separated
  - legacy FeatureSettings aggregate is not rendered from Content
  - Beta.1 showAdvancedControls mechanism is removed
- Governor diagnostics marker test: PASS
- generated wrapper marker/default logic test: PASS

Live Steam Deck Game Mode validation is still required.
