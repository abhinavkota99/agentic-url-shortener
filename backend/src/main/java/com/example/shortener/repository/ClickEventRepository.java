package com.example.shortener.repository;

import com.example.shortener.domain.ClickEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.time.Instant;
import java.util.List;

public interface ClickEventRepository extends JpaRepository<ClickEvent, Long> {
    long countByShortCode(String shortCode);
    @Query("select count(c) from ClickEvent c where c.shortCode = :code and c.clickedAt >= :since")
    long countSince(@Param("code") String code, @Param("since") Instant since);
    List<ClickEvent> findTop20ByShortCodeOrderByClickedAtDesc(String shortCode);
}
