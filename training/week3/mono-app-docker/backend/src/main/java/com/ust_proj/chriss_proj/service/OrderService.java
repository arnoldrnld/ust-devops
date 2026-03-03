package com.ust_proj.chriss_proj.service;

import com.ust_proj.chriss_proj.entity.Order;
import com.ust_proj.chriss_proj.entity.User;
import com.ust_proj.chriss_proj.repository.OrderRepository;
import com.ust_proj.chriss_proj.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class OrderService {

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private UserRepository userRepository;

    public Order createOrder(Order order) {
        // Validate that user exists
        userRepository.findById(order.getUserId())
                .orElseThrow(() -> new RuntimeException("User not found with id: " + order.getUserId()));
        
        return orderRepository.save(order);
    }

    public List<Order> getAllOrders() {
        return orderRepository.findAll();
    }

    public Optional<Order> getOrderById(Long id) {
        return orderRepository.findById(id);
    }

    public List<Order> getOrdersByUserId(Long userId) {
        return orderRepository.findByUserId(userId);
    }

    public Order updateOrder(Long id, Order orderDetails) {
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Order not found with id: " + id));
        
        order.setProduct(orderDetails.getProduct());
        order.setQuantity(orderDetails.getQuantity());
        order.setUserId(orderDetails.getUserId());
        
        return orderRepository.save(order);
    }

    public void deleteOrder(Long id) {
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Order not found with id: " + id));
        orderRepository.delete(order);
    }
}
