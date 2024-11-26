let map
// Функция инициализации карты, принимает dishId для идентификации
function initMap(dishId) {
	const mapContainer = 'map' + dishId
	const addressInput = 'addressInput' + dishId

	let placemark

	ymaps.ready(function () {
		map = new ymaps.Map(mapContainer, {
			center: [44.948237, 34.100327],
			zoom: 12,
		})

		// Обработка клика на карте для выбора адреса
		map.events.add('click', function (e) {
			const coords = e.get('coords')

			// Устанавливаем метку на карте
			if (placemark) {
				placemark.geometry.setCoordinates(coords)
			} else {
				placemark = new ymaps.Placemark(coords, {}, { draggable: true })
				map.geoObjects.add(placemark)
			}

			// Обратное геокодирование для определения адреса по координатам
			ymaps.geocode(coords).then(function (res) {
				const firstGeoObject = res.geoObjects.get(0)
				const address = firstGeoObject.getAddressLine()
				document.getElementById(addressInput).value = address
			})
		})
	})
}

// Функция для поиска адреса по введенному тексту
function searchAddress(dishId) {
	const address = document.getElementById('addressInput' + dishId).value
	ymaps.geocode(address, { results: 1 }).then(function (res) {
		const firstGeoObject = res.geoObjects.get(0)

		if (firstGeoObject) {
			const coords = firstGeoObject.geometry.getCoordinates()
			map.setCenter(coords, 15)

			// Устанавливаем метку на карте
			if (placemark) {
				placemark.geometry.setCoordinates(coords)
			} else {
				placemark = new ymaps.Placemark(coords, {}, { draggable: true })
				map.geoObjects.add(placemark)
			}
		} else {
			alert('Адрес не найден. Попробуйте указать другой адрес.')
		}
	})
}
