"use client";

import { Accordion } from "@base-ui/react/accordion";
import { ChevronDown } from "lucide-react";
import { FAQ_ITEMS } from "@/lib/faq";

export function Faq() {
  return (
    <section className="bg-gray-50 border-y border-gray-100 py-24 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Частые вопросы
          </h2>
          <p className="text-gray-500">
            Если что-то осталось непонятным — спросите в форме ниже.
          </p>
        </div>

        <Accordion.Root className="bg-white rounded-2xl border border-gray-100 divide-y divide-gray-100">
          {FAQ_ITEMS.map((item) => (
            <Accordion.Item key={item.q} className="group">
              <Accordion.Header>
                <Accordion.Trigger className="flex w-full items-center justify-between text-left px-6 py-5 hover:bg-gray-50 transition-colors">
                  <span className="font-medium text-gray-900 pr-6">{item.q}</span>
                  <ChevronDown className="h-4 w-4 text-gray-400 shrink-0 transition-transform group-data-[open]:rotate-180" />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Panel className="px-6 pb-5 text-sm text-gray-600 leading-relaxed">
                {item.a}
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion.Root>
      </div>
    </section>
  );
}
