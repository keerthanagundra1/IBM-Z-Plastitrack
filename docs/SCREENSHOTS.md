# Screenshot checklist (evidence for judges)

Capture each as a full terminal / browser window. Keep the LinuxONE prompt (`linux1@...`) visible in terminal shots.
Save into `reports/screenshots/` with the file name shown.

## 1. Platform: LinuxONE instance
- [ ] `01_instance.png`: LinuxONE Community Cloud dashboard showing the running instance (name, IP, flavor).
- [ ] `02_uname.png`: on LinuxONE: `uname -a; lscpu | head -15; free -h; cat /etc/os-release | head -3`
- [ ] `03_cpu_features.png`: `grep -o 'nnpa\|msa\|vx' /proc/cpuinfo | sort -u` (Telum AI accelerator, CPACF crypto, vector)
- [ ] `04_check_env.png`: `./scripts/run_remote.sh python scripts/check_env.py` → shows **s390x / big-endian** + library versions

## 2. Data + EDA
- [ ] `05_prepare_data.png`: `cat reports/prepare_data.log` (313k labeled rows, processed in ~93 s on LinuxONE)
- [ ] `06_eda_notebook.png`: Jupyter (lab container) with `notebooks/01_eda.ipynb` open at the "Plastic level by category" chart.
      The first output cell prints `Running on: s390x | byte order: big`.

## 3. Model training
- [ ] `07_training_output.png`: `grep -E "Platform|Rows|target|---|best|Saved" reports/train.log`
- [ ] `08_metrics.png`: `cat reports/metrics.json`
- [ ] `09_confusion_level.png`: `reports/figures/cm_plastic_level_logreg.png`
- [ ] `10_confusion_type.png`: `reports/figures/cm_plastic_type_*.png` (best model)

## 4. Generative AI
- [ ] `11_llm_cli.png`: `python scripts/run_pipeline.py --llm | tail -25` (Granite tips generated on LinuxONE)
- [ ] `12_llama_sysinfo.png`: `python -c "import llama_cpp; print(llama_cpp.llama_print_system_info().decode())"` (zDNN / NNPA backend present)

## 5. Container + security
- [ ] `13_docker_build.png`: tail of `./scripts/container.sh build`
- [ ] `14_container_status.png`: `./scripts/container.sh status` → running, healthy, s390x, user 1000, read-only, cap-drop ALL, limits
- [ ] `15_docker_images.png`: `docker images plastitrack` + `docker inspect plastitrack:1.0 --format '{{.Architecture}}'` → `s390x`
- [ ] `16_port_localhost.png`: `ss -tlnp | grep 8501` → bound to 127.0.0.1 only
- [ ] `17_ssh_tunnel.png`: laptop terminal running `ssh -L 8501:localhost:8501 ...`

## 6. App demo
- [ ] `18_app_dashboard.png`: Dashboard tab after "Load 20 demo order emails" (badges show s390x · big-endian)
- [ ] `19_app_alerts_granite.png`: Alerts tab after "Personalize with Granite" (✨ tips + "Generated on LinuxONE" tag)
- [ ] `20_app_line_items.png`: Line items tab (confidence bars + `source` column)
- [ ] `21_app_privacy.png`: Privacy tab with one email expanded, showing highlighted [NAME] [ADDRESS] [EMAIL] tags
- [ ] `22_app_privacy_panel.png`: sidebar "What we read and keep"
