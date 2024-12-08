let map

// Функция инициализации карты
function initMap(dishId) {
	const mapContainer = 'map' + dishId
	const addressInput = 'addressInput'

	// Проверка существования контейнера
	if (!document.getElementById(mapContainer)) {
		console.error(`Контейнер с ID ${mapContainer} не найден.`)
		return
	}

	console.log('Инициализация карты в контейнере:', mapContainer)

	let placemark

	ymaps.ready(function () {
		console.log('API Яндекс.Карт успешно загружен')
		map = new ymaps.Map(mapContainer, {
			center: [44.948237, 34.100327],
			zoom: 12,
		})

		// Обработка клика на карте для выбора адреса
		map.events.add('click', function (e) {
			const coords = e.get('coords')
			console.log('Координаты клика:', coords)

			// Устанавливаем метку на карте
			if (placemark) {
				placemark.geometry.setCoordinates(coords)
			} else {
				placemark = new ymaps.Placemark(coords, {}, { draggable: true })
				map.geoObjects.add(placemark)
			}

			// Обратное геокодирование для определения адреса по координатам
			ymaps.geocode(coords).then(
				function (res) {
					const firstGeoObject = res.geoObjects.get(0)
					const address = firstGeoObject
						? firstGeoObject.getAddressLine()
						: 'Адрес не найден'
					console.log('Определённый адрес:', address)
					document.getElementById(addressInput).value = address
				},
				function (err) {
					console.error('Ошибка геокодирования:', err)
				}
			)
		})
	})
}
