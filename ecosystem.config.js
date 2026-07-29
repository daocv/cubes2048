module.exports = {
  apps: [{
    name: "cubes2048",
    script: "./server.js",
    instances: 1,
    exec_mode: "fork",
    watch: false,
    env: {
      NODE_ENV: "production",
      PORT: 8080
    },
    log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    error_file: "./logs/error.log",
    out_file: "./logs/out.log",
    merge_logs: true,
    max_restarts: 10,
    restart_delay: 3000,
  }]
};