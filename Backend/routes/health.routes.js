const express = require("express");
const router = express.Router();
const mongoose = require("mongoose");

router.get("/", (req, res) => {
  const dbStatus = mongoose.connection.readyState;
  if (dbStatus === 1) {
    res.status(200).json({
      status: "OK",
      database: "connected",
      uptime: process.uptime(),
      timestamp: new Date(),
    });
  } else {
    res.status(500).json({
      status: "ERROR",
      database: "disconnected",
    });
  }
});

module.exports = router;