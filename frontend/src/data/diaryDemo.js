const now = new Date().toISOString()

export const demoDiaries = [
  {
    id: 'demo-national-beijing-palace',
    scope: 'national',
    national_spot_id: null,
    spot_id: null,
    user_name: 'demo_traveler',
    title: '北京故宫半日游路线记录',
    content: '从午门进、神武门出，重点看太和殿、珍宝馆和角楼。早到能避开人流，下午适合顺路去景山看中轴线。',
    score: 4.8,
    view_count: 268,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-national-beijing-summer',
    scope: 'national',
    national_spot_id: null,
    spot_id: null,
    user_name: 'city_walk_A',
    title: '北京颐和园西堤散步体验',
    content: '颐和园建议从北宫门进，沿昆明湖走西堤，傍晚光线很好。带老人出行可以减少爬坡，路线更轻松。',
    score: 4.7,
    view_count: 196,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-national-shanghai',
    scope: 'national',
    national_spot_id: null,
    spot_id: null,
    user_name: 'weekend_B',
    title: '上海外滩到迪士尼的两日安排',
    content: '第一晚看外滩夜景，第二天去上海迪士尼。外滩适合步行拍照，迪士尼要提前看演出时间和排队情况。',
    score: 4.6,
    view_count: 221,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-national-hangzhou',
    scope: 'national',
    national_spot_id: null,
    spot_id: null,
    user_name: 'lake_runner',
    title: '杭州西湖一圈怎么走不累',
    content: '杭州西湖推荐断桥、苏堤、雷峰塔分段游览，不必硬走全程。想拍照可以把曲院风荷放在上午。',
    score: 4.9,
    view_count: 244,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-national-xian',
    scope: 'national',
    national_spot_id: null,
    spot_id: null,
    user_name: 'history_fan',
    title: '西安兵马俑和华清宫顺路游',
    content: '西安东线可以把兵马俑和华清宫放在同一天，早上先去兵马俑，下午华清宫，晚上看演出更顺。',
    score: 4.8,
    view_count: 232,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-indoor-toilet',
    scope: 'campus',
    spot_id: 30,
    national_spot_id: null,
    user_name: 'campus_helper',
    title: '教学楼厕所和楼梯位置速记',
    content: '教学楼卫生间在东南角，靠近电梯和东侧楼梯。从入口进来先到中庭，再沿主走廊向东，看到电梯后向南即可。',
    score: 4.4,
    view_count: 188,
    media_files: [],
    created_at: now,
  },
  {
    id: 'demo-indoor-vending',
    scope: 'campus',
    spot_id: 30,
    national_spot_id: null,
    user_name: 'class_break',
    title: '教学实验楼自动售卖机补给点',
    content: '自动售卖机在北侧走廊中段，离西侧楼梯不远。课间买水很方便，但下课高峰可能会排队。',
    score: 4.2,
    view_count: 156,
    media_files: [],
    created_at: now,
  },
]

export function searchDemoDiaries(keyword = '', sortBy = 'heat') {
  const normalized = keyword.trim().toLowerCase()
  let results = demoDiaries

  if (normalized) {
    results = demoDiaries.filter((diary) => {
      const haystack = `${diary.title} ${diary.content} ${diary.user_name}`.toLowerCase()
      return haystack.includes(normalized)
    })
  }

  const sorted = [...results]
  if (sortBy === 'score') {
    sorted.sort((a, b) => (b.score || 0) - (a.score || 0))
  } else if (sortBy === 'latest') {
    sorted.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  } else {
    sorted.sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
  }
  return sorted
}
