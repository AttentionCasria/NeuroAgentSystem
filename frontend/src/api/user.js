import request from '@/utils/request'

// 1. 登录
// loginForm = { name: string, password: string }
export const loginAPI = (loginForm) => request.post('/user/login', loginForm)

// 2. 注册
// registerForm = { name: string, password: string, image: string }
export const registerAPI = (registerForm) => request.post('/user/register', registerForm)

// 3. 上传头像
// file: File 对象
export const uploadAvatarAPI = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/user/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 4. 退出登录
export const logoutAPI = () => request.post('/user/logOut')

// 5. 展示用户信息
export const getProfileAPI = () => request.get('/user/showInfo')

// 6. 修改用户信息
// data = { prePassword: string, newPassword: string, image: string }
export const updateInfoAPI = (data) => request.put('/user/showInfo/changeKey', data)
