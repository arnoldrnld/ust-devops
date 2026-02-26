package com.rnld.monolith_app.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.rnld.monolith_app.model.Product;

public interface ProductRepository extends JpaRepository<Product, Long> {
}