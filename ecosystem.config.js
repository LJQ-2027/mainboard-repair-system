module.exports = {
  apps: [
    {
      name: "motherboard-repair-beta",
      script: "ai_proxy_server.py",
      interpreter: "python3",
      cwd: "/opt/motherboard-repair-beta/app",
      env: {
        PORT: "3010",
        STATIC_ROOT: "/opt/motherboard-repair-beta/app",
        INDEX_FILE: "mainboard_repair_system_v7.4_updated.html"
      }
    },
    {
      name: "motherboard-repair-visual-qc",
      script: "visual_qc_server.py",
      interpreter: "python3",
      cwd: "/opt/motherboard-repair-beta/app",
      env: {
        VISUAL_QC_PROJECT_ROOT: "/opt/motherboard-repair-beta/app",
        VISUAL_QC_DATA_ROOT: "/opt/motherboard-repair-beta/data/visual-qc",
        VISUAL_QC_MAX_UPLOAD_BYTES: "20971520",
        VISUAL_QC_MIN_IMAGE_DIMENSION: "480",
        VISUAL_QC_MIN_FREE_BYTES: "2147483648",
        VISUAL_QC_WORKERS: "1",
        VISUAL_QC_PORT: "3020"
      }
    }
  ]
};
