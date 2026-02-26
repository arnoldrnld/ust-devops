package com.rnld.userservice.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.rnld.userservice.model.User;

public interface UserRepository extends JpaRepository<User, Long> {
}