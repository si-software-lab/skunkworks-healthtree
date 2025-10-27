FROM FROM confluentinc/cp-kafka-connect:7.6.1

# Install JDBC sink
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-jdbc:latest

# MariaDB JDBC driver
ADD https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.4.1/mariadb-java-client-3.4.1.jar /usr/share/confluent-hub-components/confluentinc-kafka-connect-jdbc/lib/

# (Optional) keep a place for custom certs if needed
RUN mkdir -p /certsubuntu:latest
LABEL authors="davidbrian"

ENTRYPOINT ["top", "-b"]