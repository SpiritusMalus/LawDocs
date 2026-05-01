module.exports = {
  apps: [
    {
      name: "lawdocs",
      script: "npm",
      args: "start",
      cwd: "/var/www/lawdocs/frontend",
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
      restart_delay: 3000,
      max_restarts: 10,
    },
  ],
};
