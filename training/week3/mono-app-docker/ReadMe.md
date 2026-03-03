# 📦 Mono App Docker  
Spring Boot + MySQL + Frontend (Dockerized – Without Docker Compose)

---

# 📌 Project Overview

This project demonstrates a **Dockerized Monolithic Application** consisting of:

- 🚀 Spring Boot Backend (REST API)
- 🗄 MySQL Database (Separate Container)
- 🖥 Static Frontend (HTML + JavaScript served via Nginx)
- 🐳 Docker-based deployment (Without Docker Compose)

The application allows users to:

- ➕ Add a user
- 📋 View all users

---

# 🏗 Architecture

Browser  
&nbsp;&nbsp;&nbsp;&nbsp;↓  
Frontend (Nginx – Port 80)  
&nbsp;&nbsp;&nbsp;&nbsp;↓ HTTP  
Backend (Spring Boot – Port 8080)  
&nbsp;&nbsp;&nbsp;&nbsp;↓ JDBC  
MySQL (Port 3306)

---

# 📂 Project Structure

mono-app-docker/
│
├── backend/
│   ├── src/
│   ├── pom.xml
│   ├── Dockerfile
│
├── frontend/
│   ├── index.html
│   ├── Dockerfile
│
└── README.md

---

# ⚙ Backend Configuration

Database configuration is defined in:

backend/src/main/resources/application.properties

Example:

spring.datasource.url=jdbc:mysql://mysql-db:3306/chriss_db  
spring.datasource.username=appuser  
spring.datasource.password=password123  
spring.jpa.hibernate.ddl-auto=update  

Important:
- `mysql-db` is the MySQL container name.
- Containers communicate using Docker network.
- Hibernate auto-creates tables using `ddl-auto=update`.

---

# 🐳 Docker Setup (Without Docker Compose)

---

## ✅ Step 1 – Create Docker Network

docker network create spring-network

---

## ✅ Step 2 – Run MySQL Container

docker run -d \
  --name mysql-db \
  --network spring-network \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=chriss_db \
  -e MYSQL_USER=appuser \
  -e MYSQL_PASSWORD=password123 \
  -p 3306:3306 \
  mysql:8.0

---

## ✅ Step 3 – Build Backend Image

cd backend  
docker build -t springboot-app .

---

## ✅ Step 4 – Run Backend Container

docker run -d \
  --name springboot-container \
  --network spring-network \
  -p 8080:8080 \
  springboot-app

Test Backend:

http://SERVER-IP:8080/api/users

---

## ✅ Step 5 – Build Frontend Image

cd ../frontend  
docker build -t frontend-app .

---

## ✅ Step 6 – Run Frontend Container

docker run -d \
  --name frontend-container \
  --network spring-network \
  -p 80:80 \
  frontend-app

---

# 🌐 Access Application

Frontend:

http://SERVER-IP

Backend API:

http://SERVER-IP:8080/api/users

---

# 🔥 Optional Improvement – Use Environment Variables (Recommended)

Instead of hardcoding database configuration in `application.properties`,  
you can externalize configuration using environment variables.

---

## Option 1 – Keep application.properties Clean

Update application.properties:

spring.datasource.url=${SPRING_DATASOURCE_URL}  
spring.datasource.username=${SPRING_DATASOURCE_USERNAME}  
spring.datasource.password=${SPRING_DATASOURCE_PASSWORD}  
spring.jpa.hibernate.ddl-auto=${SPRING_JPA_HIBERNATE_DDL_AUTO:update}

---

## Then Run Backend Like This:

docker run -d \
  --name springboot-container \
  --network spring-network \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://mysql-db:3306/chriss_db \
  -e SPRING_DATASOURCE_USERNAME=appuser \
  -e SPRING_DATASOURCE_PASSWORD=password123 \
  -e SPRING_JPA_HIBERNATE_DDL_AUTO=update \
  -p 8080:8080 \
  springboot-app

This makes your container portable across environments.

---

## Option 2 – Use .env File (Cleaner Way)

Create a file:

backend/.env

Example:

SPRING_DATASOURCE_URL=jdbc:mysql://mysql-db:3306/chriss_db  
SPRING_DATASOURCE_USERNAME=appuser  
SPRING_DATASOURCE_PASSWORD=password123  
SPRING_JPA_HIBERNATE_DDL_AUTO=update  

Then run:

docker run -d \
  --name springboot-container \
  --network spring-network \
  --env-file backend/.env \
  -p 8080:8080 \
  springboot-app

---

# 🛠 Technologies Used

- Java 17
- Spring Boot
- Spring Data JPA
- MySQL 8
- Docker
- Nginx
- HTML + JavaScript

---

# 🔍 Troubleshooting

Check running containers:

docker ps

View backend logs:

docker logs springboot-container

View MySQL logs:

docker logs mysql-db

If frontend buttons do not work:
- Check browser console (F12)
- Ensure CORS is enabled
- Ensure correct backend URL is configured

---

# 🚀 Production Improvements

For production-grade setup, consider:

- Use Docker Compose
- Add Redis
- Add Nginx Reverse Proxy
- Remove public exposure of port 8080
- Use HTTPS (SSL)
- Use Flyway or Liquibase for DB migration
- Store secrets in AWS Secrets Manager / Vault
- Add health checks
- Add container restart policy

---

# 👨‍💻 Author

Mono App Docker Demo  
Spring Boot + MySQL + Frontend