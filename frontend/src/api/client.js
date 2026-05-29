import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export default {
  // Jobs
  getJobs: (status) => api.get('/jobs', { params: { status } }).then(r => r.data),
  getJob: (id) => api.get(`/jobs/${id}`).then(r => r.data),
  updateJobStatus: (id, status, reason) => api.patch(`/jobs/${id}/status`, { status, reason }).then(r => r.data),

  // Stats
  getStats: () => api.get('/stats').then(r => r.data),

  // Profile
  getProfile: () => api.get('/profile').then(r => r.data),
  updateProfile: (data) => api.put('/profile', data).then(r => r.data),

  // Search Terms
  getSearchTerms: () => api.get('/search-terms').then(r => r.data),
  addSearchTerm: (term, source = 'user') => api.post('/search-terms', { term, source }).then(r => r.data),
  toggleSearchTerm: (id) => api.patch(`/search-terms/${id}`).then(r => r.data),

  // Blocked Companies
  getBlockedCompanies: () => api.get('/blocked-companies').then(r => r.data),
  addBlockedCompany: (name, reason) => api.post('/blocked-companies', { name, reason }).then(r => r.data),
  removeBlockedCompany: (id) => api.delete(`/blocked-companies/${id}`).then(r => r.data),

  // Chat
  getChatHistory: (jobId) => api.get(`/jobs/${jobId}/chat`).then(r => r.data),
  sendChatMessage: (jobId, message) => api.post(`/jobs/${jobId}/chat`, { message }).then(r => r.data),

  // Research Packets
  getPacket: (jobId) => api.get(`/jobs/${jobId}/packet`).then(r => r.data),
  updatePacket: (jobId, data) => api.put(`/jobs/${jobId}/packet`, data).then(r => r.data),
  addPacketFeedback: (jobId, section, feedbackText) => api.post(`/jobs/${jobId}/packet/feedback`, { section: section, feedback_text: feedbackText }).then(r => r.data),
  listPackets: () => api.get('/packets').then(r => r.data),
  generatePacket: (jobId) => api.post(`/jobs/${jobId}/packet/generate`).then(r => r.data),

  // Scraper
  triggerScrape: () => api.post('/scrape').then(r => r.data),
  getScrapeStatus: () => api.get('/scrape/status').then(r => r.data),

  // Scorer
  triggerScore: () => api.post('/score').then(r => r.data),
  getScoreStatus: () => api.get('/score/status').then(r => r.data),
  getResearchStatus: () => api.get('/research/status').then(r => r.data),

  // Tailored Resumes
  getResumes: (jobId) => api.get(`/jobs/${jobId}/resumes`).then(r => r.data),
  generateResume: (jobId, data) => api.post(`/jobs/${jobId}/resumes/generate`, data).then(r => r.data),
  autoTailorResume: (jobId) => api.post(`/jobs/${jobId}/resumes/auto-tailor`).then(r => r.data),
  downloadResume: (resumeId) => `/api/resumes/${resumeId}/download`,
  deleteResume: (resumeId) => api.delete(`/resumes/${resumeId}`).then(r => r.data),

  // Structured Resume
  getResumeAll: () => api.get('/resume/all').then(r => r.data),
  getResumeProfile: () => api.get('/resume/profile').then(r => r.data),
  updateResumeProfile: (data) => api.put('/resume/profile', data).then(r => r.data),
  getResumeExperience: () => api.get('/resume/experience').then(r => r.data),
  createResumeExperience: (data) => api.post('/resume/experience', data).then(r => r.data),
  updateResumeExperience: (id, data) => api.put(`/resume/experience/${id}`, data).then(r => r.data),
  deleteResumeExperience: (id) => api.delete(`/resume/experience/${id}`).then(r => r.data),
  reorderResumeExperience: (data) => api.put('/resume/experience/reorder', data).then(r => r.data),
  getResumeEducation: () => api.get('/resume/education').then(r => r.data),
  createResumeEducation: (data) => api.post('/resume/education', data).then(r => r.data),
  updateResumeEducation: (id, data) => api.put(`/resume/education/${id}`, data).then(r => r.data),
  deleteResumeEducation: (id) => api.delete(`/resume/education/${id}`).then(r => r.data),
  getResumeSkills: () => api.get('/resume/skills').then(r => r.data),
  createResumeSkill: (data) => api.post('/resume/skills', data).then(r => r.data),
  updateResumeSkill: (id, data) => api.put(`/resume/skills/${id}`, data).then(r => r.data),
  deleteResumeSkill: (id) => api.delete(`/resume/skills/${id}`).then(r => r.data),
};
