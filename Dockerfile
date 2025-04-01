FROM debian:latest

# Install Apache, PHP, and FFmpeg
RUN apt update && apt install -y apache2 php libapache2-mod-php ffmpeg

# Enable Apache modules
RUN a2enmod rewrite

# Set up the web directory
WORKDIR /var/www/html

# Copy PHP scripts
COPY stream.php /var/www/html/stream.php
COPY index.php /var/www/html/index.php  # New Page for Streaming UI

# Expose port 80
EXPOSE 80

# Start Apache in the foreground
CMD ["apachectl", "-D", "FOREGROUND"]