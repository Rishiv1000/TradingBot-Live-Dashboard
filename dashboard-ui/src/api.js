import axios from "axios";

const api = axios.create({
  baseURL: "",          // empty = relative URLs, Vite proxy handles /api/*
  timeout: 15000,
});

export default api;
