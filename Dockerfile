FROM debian:latest

# Install Apache, PHP, and FFmpeg
RUN apt update && apt install -y apache2 php libapache2-mod-php ffmpeg

# Enable Apache modules
RUN a2enmod rewrite

# Set up the web directory
WORKDIR /var/www/html

# Copy your PHP script to the server
COPY stream.php /var/www/html/stream.php

# Expose port 80
EXPOSE 80

# Start Apache in the foreground
CMD ["apachectl", "-D", "FOREGROUND"]
