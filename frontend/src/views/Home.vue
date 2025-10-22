<template>
  <div class="home-container">
    <!-- Left side - Image display -->
    <div class="image-section">
      <div class="image-container">
        <img 
          :src="currentImage" 
          :alt="imageAlt"
          class="main-image"
          @error="handleImageError"
        />
        <div class="image-frame"></div>
      </div>
    </div>

    <!-- Right side - Chat interface -->
    <div class="chat-section">
      <Conversation />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Conversation from '../components/Conversation.vue'

const currentImage = ref('/src/assets/imgs/balloon.jpg')
const imageAlt = ref('Two girls with pink balloons - friendly cartoon illustration')

const handleImageError = () => {
  console.log('Image failed to load, using fallback')
  // Could set a fallback image here
}
</script>

<style scoped>
.home-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  font-family: 'Comic Sans MS', cursive, sans-serif;
}

/* Image Section */
.image-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%);
}

.image-container {
  position: relative;
  max-width: 100%;
  max-height: 100%;
}

.main-image {
  width: 100%;
  height: auto;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s ease;
}

.main-image:hover {
  transform: scale(1.02);
}

.image-frame {
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  bottom: -10px;
  border: 4px solid #ff6b9d;
  border-radius: 25px;
  background: linear-gradient(45deg, #ff6b9d, #c44569);
  z-index: -1;
  opacity: 0.3;
}

.chat-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(45deg, #fecfef 0%,#fecfef 70%, #ffa8ab 100%);
}

/* Responsive Design */
@media (max-width: 768px) {
  .home-container {
    flex-direction: column;
  }
  
  .image-section {
    flex: 0 0 40vh;
  }
  
  .chat-section {
    flex: 1;
  }
  
  .main-image {
    max-height: 35vh;
  }
}
</style>
