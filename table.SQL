-- 1. สร้างฐานข้อมูล 
CREATE DATABASE IF NOT EXISTS `cls_ska` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `cls_ska`;

-- 2. ลบตารางเก่าออกก่อน 
DROP TABLE IF EXISTS `requests`;
DROP TABLE IF EXISTS `users`;

-- 3. สร้างตารางเก็บข้อมูลผู้ใช้งาน 
CREATE TABLE `users` (
  `id` varchar(50) NOT NULL,
  `username` varchar(100) NOT NULL,
  `email` varchar(255) DEFAULT NULL,      -- เพิ่มรองรับการแจ้งเตือน
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `phone` varchar(50) DEFAULT NULL,       -- เพิ่มแสดงผลใน Dashboard
  `role` enum('admin','user','superadmin') NOT NULL,
  `status` varchar(20) DEFAULT 'pending', -- สำหรับระบบอนุมัติผู้ใช้
  `profile_pic` varchar(255) DEFAULT NULL,
  `additional_emails` text DEFAULT NULL,
  `additional_phones` text DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. สร้างตารางเก็บข้อมูลคำขอเข้าพื้นที่ (ฉบับอัปเดต มี Soft Delete)
CREATE TABLE `requests` (
  `id` varchar(50) NOT NULL,
  `user_id` varchar(50) NOT NULL,
  `username` varchar(100) NOT NULL,
  `req_type` varchar(50) DEFAULT NULL,
  `req_cat` varchar(50) DEFAULT NULL,
  `req_date` date DEFAULT NULL,
  `req_time` time DEFAULT NULL,
  `company` varchar(255) DEFAULT NULL,
  `vendor_company` varchar(255) DEFAULT NULL,
  `dcf` varchar(100) DEFAULT NULL,
  `mobile` varchar(50) DEFAULT NULL,
  `vehicle_reg` varchar(100) DEFAULT NULL,
  `requester_name` varchar(255) DEFAULT NULL,
  `objective` text DEFAULT NULL,
  `detail_work` text DEFAULT NULL,
  `work_types` json DEFAULT NULL,
  `risk` varchar(10) DEFAULT NULL,
  `areas` json DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `start_time` time DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `end_time` time DEFAULT NULL,
  `workers` json DEFAULT NULL,
  `signature` longtext DEFAULT NULL,
  `status` varchar(50) DEFAULT 'Pending',
  `approver_name` varchar(255) DEFAULT NULL,
  `approver_comment` text DEFAULT NULL,
  `approver_signature` longtext DEFAULT NULL,
  `is_deleted_by_user` tinyint(1) DEFAULT 0, -- สำหรับระบบ Soft Delete
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id_idx` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;