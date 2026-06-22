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
    }
  ]
};
