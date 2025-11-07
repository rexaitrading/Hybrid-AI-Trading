# Nightly CI (06:30 PT)

- lint.yml and CodeQL.yml include dual-cron:
  - \30 14 * * *\ (06:30 PT during PST / UTC-8)
  - \30 13 * * *\ (06:30 PT during PDT / UTC-7)