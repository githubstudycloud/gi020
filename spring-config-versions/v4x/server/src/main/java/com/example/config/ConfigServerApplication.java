package com.example.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;
import org.springframework.context.annotation.Bean;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Boot 4.x Config Server
 *
 * 4.x 主要变化（相比 3.x）：
 * 1. 需要 Java 21+
 * 2. Spring Framework 7.x（更好的虚拟线程支持）
 * 3. 移除了更多过时 API（如 spring.mvc.pathmatch.use-suffix-pattern）
 * 4. 默认启用虚拟线程（Virtual Threads，Loom）
 * 5. 更深度的 GraalVM 原生镜像支持
 * 6. spring-cloud-config 的 API 基本保持稳定，配置方式与 3.x 一致
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}

/**
 * Spring Security 6.x 配置（4.x 使用 Spring Security 7.x）
 *
 * 4.x 与 3.x 的 Security 配置方式基本一致
 * 主要区别：更严格的默认安全策略，部分旧 API 进一步清理
 */
@EnableWebSecurity
class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                .requestMatchers("/encrypt/**", "/decrypt/**").authenticated()
                .anyRequest().authenticated()
            )
            .httpBasic(basic -> {});
        return http.build();
    }
}
