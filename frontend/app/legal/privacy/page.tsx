import Link from "next/link";

export const metadata = {
  title: "Политика конфиденциальности — LawDocs",
  robots: { index: false },
};

export default function PrivacyPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-2">Политика обработки персональных данных law-docs.ru</h1>
      <p className="text-sm text-gray-400 mb-1">Последнее обновление: 25 мая 2026 г.</p>
      <p className="text-sm text-gray-400 mb-1">Вступает в силу: 25 мая 2026 г.</p>
      <p className="text-sm text-gray-400 mb-8">Версия: 2.0 (End-to-End Encryption)</p>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-8 not-prose">
        <p className="font-semibold text-gray-800 mb-2">🔑 Краткое резюме для спешащих</p>
        <p className="text-gray-700 text-sm">
          <strong>Коротко:</strong> Мы собираем минимум данных, всё шифруем (особенно чувствительное),
          вы всегда можете удалить аккаунт, и даже мы не можем прочитать ваши данные (это хорошо).
        </p>
        <p className="text-gray-700 text-sm mt-2">
          <strong>Тип защиты:</strong> End-to-End Encryption (E2EE) — одна из самых надёжных в мире.
        </p>
        <p className="text-gray-700 text-sm mt-1">
          <strong>Передаём ли за границу?</strong> Нет, всё остаётся в России.
        </p>
        <p className="text-gray-700 text-sm mt-1">
          <strong>Можете ли вы удалить данные?</strong> Да, в личном кабинете или по email.
        </p>
      </div>

      <h2 className="text-xl font-semibold mt-8 mb-3">1. КТО ОБРАБАТЫВАЕТ ВАШИ ДАННЫЕ</h2>
      <table className="w-full text-sm text-gray-700 border-collapse mb-4">
        <tbody>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap align-top">Сервис</td>
            <td className="py-2">law-docs.ru — платформа для генерации юридических документов</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap align-top">Компания</td>
            <td className="py-2">ИП Тихоненко Евгений Юрьевич</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap align-top">ИНН</td>
            <td className="py-2">504414138460</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap align-top">Контакт по ПД</td>
            <td className="py-2 text-gray-400">law-docs@gmail.com</td>
          </tr>
        </tbody>
      </table>

      <h2 className="text-xl font-semibold mt-8 mb-3">2. КАКИЕ ДАННЫЕ МЫ СОБИРАЕМ</h2>

      <p className="font-medium text-gray-700 mt-4 mb-2">При регистрации</p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Email (обязательно)</li>
        <li>Имя (опционально)</li>
      </ul>

      <p className="font-medium text-gray-700 mt-4 mb-2">При оформлении документа (заполнение формы)</p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Полное имя (ФИО)</li>
        <li>Номер телефона</li>
        <li>Почтовый адрес</li>
        <li>Email (если другой)</li>
        <li>Наименование ответчика (магазина, банка и т.д.)</li>
        <li>Описание вашей проблемы</li>
        <li>Реквизиты счёта (если нужны для документа)</li>
      </ul>

      <p className="font-medium text-gray-700 mt-4 mb-2">Автоматически</p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>IP адрес</li>
        <li>Информация о браузере и ОС</li>
        <li>Cookies (для функционирования сайта)</li>
        <li>Дата и время посещения</li>
      </ul>

      <p className="font-medium text-gray-700 mt-4 mb-2">Что мы НЕ собираем</p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Номера кредитных карт (обрабатывает платёжная система)</li>
        <li>Паспортные данные</li>
        <li>Биометрические данные</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">3. КАК МЫ ЗАЩИЩАЕМ ВАШИ ДАННЫЕ</h2>

      <h3 className="text-lg font-semibold mt-4 mb-2">End-to-End Encryption (E2EE) — ОСНОВНАЯ ЗАЩИТА</h3>

      <p className="font-medium text-gray-700 mb-2">Что это значит по-русски:</p>
      <ol className="list-decimal pl-6 text-gray-700 space-y-3">
        <li>
          <strong>При регистрации:</strong> Ваш браузер генерирует два криптографических ключа.
          Приватный ключ (закрытый) — остаётся в браузере, никуда не отправляется.
          Публичный ключ (открытый) — отправляется на сервер.
        </li>
        <li>
          <strong>Когда вы заполняете форму:</strong> Все данные шифруются ДО отправки на сервер.
          Ваше имя: «Иван Петров» → «MIIBIjANBgkqhkiG9w0BAQE...» (зашифровано).
          На сервер попадает только шифр, не текст.
        </li>
        <li>
          <strong>На сервере:</strong> Мы храним зашифрованные данные.
          Мы видим: «MIIBIjANBgkqhkiG9w0BAQE...».
          Мы НЕ видим: «Иван Петров».
          Расшифровать без вашего ключа невозможно.
        </li>
        <li>
          <strong>Когда вы открываете заказ:</strong> Браузер расшифровывает данные.
          Браузер получает: «MIIBIjANBgkqhkiG9w0BAQE...».
          Браузер расшифровывает: «Иван Петров».
          ТОЛЬКО вы видите открытые данные.
        </li>
      </ol>

      <p className="font-medium text-gray-700 mt-4 mb-2">Почему это хорошо?</p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>✅ Если сайт взломают, хакер получит только шифр (бесполезен)</li>
        <li>✅ Даже наши сотрудники не могут прочитать ваши данные</li>
        <li>✅ При запросе суда мы не можем выдать открытые данные (их нет!)</li>
        <li>✅ Максимум конфиденциальности (Zero-Knowledge Architecture)</li>
      </ul>

      <p className="font-medium text-gray-700 mt-6 mb-3">Другие меры защиты</p>
      <table className="w-full text-sm text-gray-700 border-collapse">
        <tbody>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">HTTPS/TLS 1.3</td>
            <td className="py-2">Все данные в пути шифруются</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">Fernet шифрование</td>
            <td className="py-2">Email дополнительно защищён на сервере</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">Логирование доступа</td>
            <td className="py-2">Все обращения к данным записываются</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">Ежедневные бэкапы</td>
            <td className="py-2">Если что-то сломается, восстановим</td>
          </tr>
          <tr>
            <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">24/7 мониторинг</td>
            <td className="py-2">Проверяем на попытки взлома</td>
          </tr>
        </tbody>
      </table>

      <h2 className="text-xl font-semibold mt-8 mb-3">4. ПОЧЕМУ МЫ ОБРАБАТЫВАЕМ ДАННЫЕ</h2>
      <p className="text-gray-700 leading-relaxed">
        <strong>На основании:</strong> Вашего явного согласия (чекбокс «Я согласен с политикой»)
      </p>
      <p className="text-gray-700 leading-relaxed mt-2">
        <strong>Правовая база:</strong> Федеральный закон № 152-ФЗ «О защите персональных данных»
      </p>
      <p className="text-gray-700 leading-relaxed mt-2">
        <strong>Как получаем согласие:</strong>
      </p>
      <div className="bg-gray-50 border border-gray-200 rounded p-3 mt-2 font-mono text-sm not-prose">
        <p>[☑] Я согласен с Политикой обработки персональных данных law-docs.ru</p>
        <p className="text-gray-500 text-xs mt-1">(ссылка на эту страницу)</p>
        <p className="mt-2">[Оформить претензию] ← кнопка работает только если согласие дано</p>
      </div>
      <p className="text-gray-700 leading-relaxed mt-3">
        При согласии мы фиксируем: дату и время, ваш IP адрес, версию политики.
      </p>
      <p className="text-gray-700 leading-relaxed mt-2">
        <strong>Вы можете отозвать согласие в любой момент</strong> — в личном кабинете или по email.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">5. ДЛЯ ЧЕГО НУЖНЫ НАШИ ДАННЫЕ</h2>
      <table className="w-full text-sm text-gray-700 border-collapse">
        <thead>
          <tr className="border-b border-gray-300">
            <th className="py-2 pr-4 text-left font-medium text-gray-600">Цель</th>
            <th className="py-2 pr-4 text-left font-medium text-gray-600">Данные</th>
            <th className="py-2 text-left font-medium text-gray-600">Срок</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Создание аккаунта</td>
            <td className="py-2 pr-4">Email</td>
            <td className="py-2 whitespace-nowrap">До удаления аккаунта</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Оформление документа</td>
            <td className="py-2 pr-4">Форма заказа (вся зашифрована)</td>
            <td className="py-2 whitespace-nowrap">3 года</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Отправка документа</td>
            <td className="py-2 pr-4">Email</td>
            <td className="py-2 whitespace-nowrap">До времени заказа</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Обработка платежа</td>
            <td className="py-2 pr-4">Email + сумма</td>
            <td className="py-2 whitespace-nowrap">До времени платежа</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Налоговый учёт</td>
            <td className="py-2 pr-4">История платежей</td>
            <td className="py-2 whitespace-nowrap">7 лет (закон)</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4">Безопасность</td>
            <td className="py-2 pr-4">Логи доступа</td>
            <td className="py-2 whitespace-nowrap">1 год</td>
          </tr>
          <tr>
            <td className="py-2 pr-4">Аналитика сайта</td>
            <td className="py-2 pr-4">IP, браузер (ОБЕЗЛИЧЕНЫ)</td>
            <td className="py-2 whitespace-nowrap">13 месяцев</td>
          </tr>
        </tbody>
      </table>
      <p className="text-gray-700 mt-3">
        <strong>Важно:</strong> Мы не продаём ваши данные, не используем для маркетинга и не передаём в соцсети.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">6. СРОКИ ХРАНЕНИЯ</h2>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li><strong>Email в аккаунте:</strong> До удаления аккаунта</li>
        <li><strong>Данные заказа:</strong> 3 года (потом автоматически удаляются)</li>
        <li><strong>История платежей:</strong> 7 лет (требование налогового кодекса)</li>
        <li><strong>Логи безопасности:</strong> 1 год</li>
        <li><strong>Cookies:</strong> 13 месяцев</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">7. КОМУ МЫ ПЕРЕДАЁМ ДАННЫЕ</h2>
      <table className="w-full text-sm text-gray-700 border-collapse">
        <thead>
          <tr className="border-b border-gray-300">
            <th className="py-2 pr-4 text-left font-medium text-gray-600">Организация</th>
            <th className="py-2 pr-4 text-left font-medium text-gray-600">Для чего</th>
            <th className="py-2 text-left font-medium text-gray-600">Договор</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium">YooKassa</td>
            <td className="py-2 pr-4">Обработка платежей</td>
            <td className="py-2">✓ Да</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium">Email сервис</td>
            <td className="py-2 pr-4">Отправка документов</td>
            <td className="py-2">✓ Да</td>
          </tr>
          <tr className="border-b border-gray-200">
            <td className="py-2 pr-4 font-medium">Яндекс.Метрика</td>
            <td className="py-2 pr-4">Аналитика (обезличенно)</td>
            <td className="py-2">✓ Да</td>
          </tr>
          <tr>
            <td className="py-2 pr-4 font-medium">Правоохранительные органы</td>
            <td className="py-2 pr-4">По решению суда</td>
            <td className="py-2">Требуется ордер</td>
          </tr>
        </tbody>
      </table>
      <p className="text-gray-700 mt-3">
        <strong>Важно про суд и РКН:</strong> Даже при наличии судебного решения мы можем передать
        только то, что хранится на сервере — зашифрованные данные. Ключей для расшифровки у нас нет,
        поэтому передать открытые данные физически невозможно.
      </p>
      <p className="text-gray-700 mt-2">
        <strong>НЕ передаём:</strong> За границу, в соцсети, рекламным сетям.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">8. ВАШИ ПРАВА</h2>
      <p className="text-gray-700 leading-relaxed mb-3">Вы можете:</p>

      <h3 className="text-base font-semibold text-gray-700 mt-3 mb-1">Получить доступ к своим данным</h3>
      <ul className="list-disc pl-6 text-gray-700 space-y-1 text-sm">
        <li>Личный кабинет → Настройки → «Скачать мои данные»</li>
        <li>Получите файл JSON/CSV со всеми данными</li>
        <li>Срок: до 30 дней</li>
      </ul>

      <h3 className="text-base font-semibold text-gray-700 mt-3 mb-1">Исправить ошибочные данные</h3>
      <ul className="list-disc pl-6 text-gray-700 space-y-1 text-sm">
        <li>Личный кабинет → Настройки → «Изменить профиль»</li>
        <li>Срок: немедленно</li>
      </ul>

      <h3 className="text-base font-semibold text-gray-700 mt-3 mb-1">Удалить свои данные (право быть забытым)</h3>
      <ul className="list-disc pl-6 text-gray-700 space-y-1 text-sm">
        <li>Личный кабинет → Настройки → «Удалить аккаунт»</li>
        <li>Потребуется подтверждение по email</li>
        <li>Срок: до 30 дней</li>
        <li><strong>Внимание:</strong> удаление необратимо</li>
      </ul>

      <h3 className="text-base font-semibold text-gray-700 mt-3 mb-1">Ограничить обработку</h3>
      <ul className="list-disc pl-6 text-gray-700 space-y-1 text-sm">
        <li>Личный кабинет → Настройки → «Ограничить обработку»</li>
        <li>Данные не удаляются, но не обрабатываются</li>
        <li>Срок: до 30 дней</li>
      </ul>

      <h3 className="text-base font-semibold text-gray-700 mt-3 mb-1">Отозвать согласие</h3>
      <ul className="list-disc pl-6 text-gray-700 space-y-1 text-sm">
        <li>Личный кабинет → Настройки → «Отозвать согласие»</li>
        <li>Обработка прекращается немедленно</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">9. СПЕЦИАЛЬНЫЕ ВОПРОСЫ ПО E2EE</h2>

      <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">Что если я переустановлю браузер?</h3>
      <p className="text-gray-700 text-sm leading-relaxed">
        <strong>Не паникуйте!</strong> Откройте наш сайт в новом браузере, нажмите «Восстановить доступ»,
        введите свой пароль — мы восстановим ваш приватный ключ из защищённого backup.
      </p>

      <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">Что если я забыл пароль?</h3>
      <p className="text-gray-700 text-sm leading-relaxed">
        <strong>Это нормально.</strong> Сбросьте пароль как обычно (Forgot Password), потом восстановите доступ к E2EE данным.
      </p>

      <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">Что если потерять телефон/ноутбук?</h3>
      <p className="text-gray-700 text-sm leading-relaxed">
        <strong>Доступ не потеряется.</strong> Резервная копия ключа хранится на сервере
        (зашифрована вашим паролем) — можно восстановить на другом устройстве, введя пароль в браузере.
      </p>

      <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">Может ли служба поддержки видеть мои данные?</h3>
      <p className="text-gray-700 text-sm leading-relaxed">
        <strong>Нет.</strong> Они видят только: что вы создали заказ, статус платежа, дату и время.
        ФИО, адрес, описание проблемы — всё зашифровано E2EE и недоступно нам.
      </p>

      <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">Может ли РКН требовать мои данные?</h3>
      <p className="text-gray-700 text-sm leading-relaxed">
        <strong>Может.</strong> Но даже при ордере суда мы не можем выдать открытые данные — ключей
        для расшифровки на сервере нет. Физически невозможно расшифровать без вашего браузера.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">10. СВЯЗЬ С НАМИ</h2>
      <p className="text-gray-700 leading-relaxed mb-3">По вопросам персональных данных:</p>
      <p className="text-gray-700">
        <strong>Email:</strong>{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">lawdocsru@gmail.com</a>
      </p>
      <p className="text-gray-700 mt-2">Мы ответим в течение 30 дней.</p>
      <h2 className="text-xl font-semibold mt-8 mb-3">11. СОГЛАСИЕ</h2>
      <p className="text-gray-700 leading-relaxed">
        Нажимая «Оформить претензию» вы подтверждаете что:
      </p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Прочитали эту политику</li>
        <li>Согласны с обработкой персональных данных</li>
        <li>Понимаете что ваши данные защищены E2EE</li>
        <li>Вам 18+ (или есть согласие родителей)</li>
      </ul>

      <div className="mt-8 pt-6 border-t border-gray-200 text-xs text-gray-500 not-prose">
        <p>Версия: 2.0 (End-to-End Encryption)</p>
        <p>Дата: 25 мая 2026 г.</p>
        <p>Статус: Опубликована и действует</p>
        <p>Соответствие: 152-ФЗ + Privacy-by-Design</p>
      </div>
    </article>
  );
}
