// pages/mine/mine.js
const api = require('../../utils/api')

Page({
  data: {
    activeTab: 'history',        // history | favorite
    stats: { historyCount: 0, favoriteCount: 0, todayCount: 0 },
    list: [],
    page: 1,
    size: 20,
    hasMore: true,
    loading: false,
    inited: false
  },

  onShow() {
    // 每次显示都刷新（进入/切回都要看到最新数据）
    this.refreshAll()
  },

  refreshAll() {
    // 刷新统计 + 重置列表 + 拉第一页
    api.getUserStats().then((stats) => {
      this.setData({ stats })
    }).catch(() => {})
    this.setData({ list: [], page: 1, hasMore: true, inited: false })
    this.loadMore()
  },

  onSwitchTab(e) {
    const tab = e.currentTarget.dataset.tab
    if (tab === this.data.activeTab) return
    wx.vibrateShort({ type: 'light' })
    this.setData({
      activeTab: tab,
      list: [],
      page: 1,
      hasMore: true,
      inited: false
    })
    this.loadMore()
  },

  loadMore() {
    if (this.data.loading || !this.data.hasMore) return
    this.setData({ loading: true })
    const isHistory = this.data.activeTab === 'history'
    const fetch = isHistory ? api.listHistory : api.listFavorites
    fetch(this.data.page, this.data.size).then((res) => {
      // 把时间戳格式化成可读字符串
      const now = Date.now()
      const list = (res.list || []).map((item) => {
        item._time = formatTime(item.createdAt, now)
        item._contentPreview = truncate(item.content, 60)
        return item
      })
      this.setData({
        list: this.data.list.concat(list),
        page: this.data.page + 1,
        hasMore: res.hasMore,
        loading: false,
        inited: true
      })
    }).catch((err) => {
      this.setData({ loading: false, inited: true })
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    })
  },

  onReachBottom() {
    this.loadMore()
  },

  onPullDownRefresh() {
    this.refreshAll()
    setTimeout(() => wx.stopPullDownRefresh(), 800)
  },

  /**
   * 点击列表项 —— 跳回结果页展示这条记录（复用结果页 UI）
   */
  onTapItem(e) {
    const item = e.currentTarget.dataset.item
    // 把 record 写入 lastRoast，跳转到 result 页复用已有渲染逻辑
    wx.setStorageSync('lastRoast', {
      roastId: item.roastId,
      content: item.content,
      style: item.style,
      styleName: item.styleName,
      styleEmoji: item.styleEmoji
    })
    wx.navigateTo({ url: `/pages/result/result?roastId=${item.roastId}` })
  },

  /**
   * 收藏 / 取消收藏
   */
  onToggleFavorite(e) {
    e.stopPropagation && e.stopPropagation()
    const roastId = e.currentTarget.dataset.id
    const wasFav = e.currentTarget.dataset.fav
    const call = wasFav ? api.removeFavorite : api.addFavorite
    call(roastId).then(() => {
      wx.vibrateShort({ type: 'light' })
      // 就地更新
      const list = this.data.list.map((item) => {
        if (item.roastId === roastId) item.isFavorite = !wasFav
        return item
      })
      // 收藏 Tab 下取消收藏 → 从列表移除
      let finalList = list
      if (this.data.activeTab === 'favorite' && wasFav) {
        finalList = list.filter((item) => item.roastId !== roastId)
      }
      this.setData({ list: finalList })
      // 顺带刷统计
      api.getUserStats().then((stats) => this.setData({ stats })).catch(() => {})
    }).catch((err) => {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    })
  },

  /**
   * 长按删除历史（只对历史 Tab 生效）
   */
  onLongPressItem(e) {
    if (this.data.activeTab !== 'history') return
    const roastId = e.currentTarget.dataset.id
    wx.showModal({
      title: '删除这条记录？',
      content: '删除后不可恢复，且会自动取消收藏',
      confirmColor: '#ff5252',
      success: (res) => {
        if (!res.confirm) return
        api.deleteHistory(roastId).then(() => {
          wx.vibrateShort({ type: 'medium' })
          const list = this.data.list.filter((item) => item.roastId !== roastId)
          this.setData({ list })
          api.getUserStats().then((stats) => this.setData({ stats })).catch(() => {})
          wx.showToast({ title: '已删除', icon: 'success' })
        }).catch((err) => {
          wx.showToast({ title: err.message || '删除失败', icon: 'none' })
        })
      }
    })
  },

  onNavIndex() {
    wx.switchTab({ url: '/pages/index/index' })
  },

  onNavAgreement() {
    wx.navigateTo({ url: '/pages/agreement/agreement' })
  },

  onNavPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' })
  },

  onNavAbout() {
    wx.navigateTo({ url: '/pages/about/about' })
  }
})

// ---------- 工具 ----------
function pad(n) { return n < 10 ? '0' + n : '' + n }

function formatTime(ms, nowMs) {
  const diff = nowMs - ms
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 24 * 60 * 60 * 1000) return Math.floor(diff / 3600000) + '小时前'
  if (diff < 7 * 24 * 60 * 60 * 1000) return Math.floor(diff / 86400000) + '天前'
  const d = new Date(ms)
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.substring(0, n) + '...' : s
}
