<template>
  <div class="home-container">
    <!-- Left side - Image display -->
    <div class="image-section">
      <button @click="handleSwitchImage" class="switch-image-button">
        🔄 Switch Image
      </button>
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
      <Conversation :selectedImagePath="currentImage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Conversation from '../components/Conversation.vue'

const route = useRoute()
const router = useRouter()

const currentImage = ref('/imgs/balloon.jpg')
const imageAlt = ref('Two girls with pink balloons - friendly cartoon illustration')

const handleImageError = () => {
  console.log('Image failed to load, using fallback')
  // Could set a fallback image here
}

const handleSwitchImage = () => {
  // Navigate back to image selection
  router.push('/')
}

// Get image from route query parameter
onMounted(() => {
  const imagePath = route.query.image as string
  if (imagePath) {
    currentImage.value = imagePath
    
    // Update alt text based on selected image
    if (imagePath.includes('balloon.jpg')) {
      imageAlt.value = 'Two girls with pink balloons - friendly cartoon illustration'
    } else if (imagePath.includes('bend.jpg')) {
      imageAlt.value = 'Bending light mystery - scientific exploration'
    } else if (imagePath.includes('salt.jpg')) {
      imageAlt.value = 'Salt mystery - scientific exploration'
    }
  } else {
    // If no image is selected, redirect back to home
    router.push('/')
  }
})
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%);
  position: relative;
}

.switch-image-button {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(102, 126, 234, 0.9);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.6);
  padding: 10px 20px;
  border-radius: 25px;
  cursor: pointer;
  font-size: 1em;
  font-weight: bold;
  transition: all 0.3s ease;
  white-space: nowrap;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.switch-image-button:hover {
  background: rgba(102, 126, 234, 1);
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.switch-image-button:active {
  transform: scale(0.95);
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
  
  .switch-image-button {
    top: 10px;
    left: 10px;
    padding: 8px 16px;
    font-size: 0.9em;
  }
  
  .chat-section {
    flex: 1;
  }
  
  .main-image {
    max-height: 35vh;
  }
}
</style>
