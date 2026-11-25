FROM alpine:latest

RUN mkdir -p /backups

COPY seed-backup.sh /usr/local/bin/seed-backup.sh
RUN chmod +x /usr/local/bin/seed-backup.sh

CMD ["/bin/sh", "-c", "/usr/local/bin/seed-backup.sh && tail -f /dev/null"]
