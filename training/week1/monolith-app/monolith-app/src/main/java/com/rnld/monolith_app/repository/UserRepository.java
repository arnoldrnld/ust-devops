package com.rnld.monolith_app.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.rnld.monolith_app.model.User;

public interface UserRepository extends JpaRepository<User, Long> {
}