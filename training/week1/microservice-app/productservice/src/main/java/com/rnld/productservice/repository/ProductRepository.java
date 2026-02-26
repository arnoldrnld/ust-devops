package com.rnld.productservice.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.rnld.productservice.model.Product;

public interface ProductRepository extends JpaRepository<Product, Long> {
}